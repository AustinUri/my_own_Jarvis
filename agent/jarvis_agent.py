from __future__ import annotations

import json
import re
from typing import Any, Callable

from agent.conversation import ConversationMemory
from agent.policy import RequestPolicy
from agent.provider import OpenAICompatibleProvider, ProviderError
from core.config import AppConfig
from core.events import AssistantReply, ToolAction
from llm.brain import Brain as LegacyFallbackBrain
from tools.registry import ToolRegistry
from tools.web_tools import WebAnswer

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


class JarvisAgent:
    """The conversational agent.

    The provider decides *what* to do. ToolRegistry decides *what it is allowed
    to touch*. RequestPolicy decides whether an action is appropriate for the
    user's wording. This keeps the model intelligent without handing it raw
    shell/computer ownership.
    """

    def __init__(
        self,
        config: AppConfig,
        tools: ToolRegistry,
        log: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.tools = tools
        self.log = log or (lambda _message: None)
        self.memory = ConversationMemory(config.conversation_history_turns)
        self._fallback = LegacyFallbackBrain(config)
        self._provider = self._build_provider()

    def reload_config(self) -> None:
        self.memory.set_max_turns(self.config.conversation_history_turns)
        self._fallback.config = self.config
        self._provider = self._build_provider()

    def clear_memory(self) -> None:
        self.memory.clear()
        self.log("Conversation memory cleared.")

    def detect_language(self, text: str) -> str:
        if self.config.language_mode in {"Hebrew", "English"}:
            return "he" if self.config.language_mode == "Hebrew" else "en"
        return "he" if HEBREW_RE.search(text) else "en"

    def provider_status(self) -> str:
        try:
            models = self._provider.list_models()
            return f"AI server OK. Loaded model(s): {', '.join(models) if models else 'none'}"
        except ProviderError as exc:
            return str(exc)

    def analyze_camera_frame(self, data_url: str, prompt: str) -> str:
        """Analyze one explicitly shared camera frame with the configured VLM.

        The workspace owns camera permission and supplies only the latest frame.
        This method never opens the camera itself.
        """
        question = (prompt or "Describe what is visible in the camera.").strip()
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS visual perception. Describe only what is visibly supported by the image. "
                    "Do not identify unknown people by name and do not infer sensitive personal traits. "
                    "Be concise and practical."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                ],
            },
        ]
        message = self._provider.chat(messages=messages, tools=None, temperature=0.15)
        content = str(message.get("content") or "").strip()
        if not content:
            raise ProviderError("The vision model returned an empty response.")
        return content

    def process(self, user_text: str) -> AssistantReply:
        language = self.detect_language(user_text)
        policy = RequestPolicy.from_text(user_text)
        try:
            reply = self._run_agent_loop(user_text, language, policy)
        except ProviderError as exc:
            self.log(f"AI provider unavailable; degraded local fallback used. {exc}")
            reply = self._run_fallback(user_text, language)
        self.memory.add_turn(user_text, reply.gui_text)
        return reply

    def _build_provider(self) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            base_url=self.config.ai_base_url,
            model=self.config.ai_model_name,
            api_key=self.config.ai_api_key,
            timeout=float(self.config.ai_timeout_seconds),
        )

    def _run_agent_loop(self, user_text: str, language: str, policy: RequestPolicy) -> AssistantReply:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(language)},
            *self.memory.snapshot(),
            {"role": "user", "content": user_text},
        ]
        tools = self.tools.definitions()
        tool_trace: list[str] = []

        max_rounds = max(1, min(10, int(self.config.ai_max_tool_rounds)))
        self.log("Agent: reasoning started.")
        for _round in range(max_rounds):
            self.log(f"Agent: model round {_round + 1} of {max_rounds}.")
            assistant_message = self._provider.chat(
                messages=messages,
                tools=tools,
                temperature=float(self.config.ai_temperature),
            )
            calls = assistant_message.get("tool_calls") or []
            if calls:
                messages.append(self._assistant_message_for_history(assistant_message))
                for call in calls:
                    tool_call_id, name, args = self._parse_tool_call(call)
                    allowed, reason = policy.authorize(name, self.config.auto_open_explicit_only)
                    if allowed:
                        arg_preview = json.dumps(args, ensure_ascii=False, default=str)[:360] if args else ""
                        self.log(f"Tool requested: {name}{' ' + arg_preview if arg_preview else ''}")
                        result = self.tools.run(ToolAction(name=name, args=args))
                        model_result = self.tools.result_for_model(result)
                        tool_trace.append(name)
                        if isinstance(result, WebAnswer):
                            self.log(f"Tool completed: {name} via {result.provider}")
                        else:
                            self.log(f"Tool completed: {name}")
                    else:
                        model_result = f"TOOL DENIED BY POLICY: {reason}"
                        tool_trace.append(f"{name} (denied)")
                        self.log(f"Tool denied: {name} — {reason}")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": model_result,
                        }
                    )
                continue

            content = str(assistant_message.get("content") or "").strip()
            if not content:
                raise ProviderError("The model returned neither a reply nor a tool call.")
            self.log("Agent: final response ready.")
            parsed = self._parse_final_response(content, language)
            return AssistantReply(
                user_language=language,
                intent=parsed["intent"],
                gui_text=self._ensure_address(parsed["gui_text"], language),
                spoken_text=self._ensure_address(parsed["spoken_text"], "en"),
                raw_user_text=user_text,
                tool_trace=tool_trace,
                provider=self.config.ai_provider,
            )

        raise ProviderError("Jarvis reached the maximum tool-call rounds without a final answer.")

    def _run_fallback(self, user_text: str, language: str) -> AssistantReply:
        personal = self._fallback._personal_domain_reply(user_text, language)
        base = personal or self._fallback._fallback_reply(user_text, language)
        if base.tool is None:
            return self._fallback._apply_personality(base)
        result = self.tools.run(base.tool)
        if isinstance(result, WebAnswer):
            gui = result.to_gui_text()
            spoken = result.spoken_text
        else:
            gui = str(result)
            spoken = str(result)[:220] if result else "Done."
        reply = AssistantReply(
            user_language=language,
            intent=base.intent,
            gui_text=gui,
            spoken_text=spoken,
            raw_user_text=user_text,
            tool_trace=[base.tool.name],
            provider="degraded fallback",
        )
        return self._fallback._apply_personality(reply)

    def _system_prompt(self, language: str) -> str:
        address = (self.config.address_name or "sir").strip()
        tone = self.config.tone_mode.lower()
        verbosity = self.config.verbosity_mode.lower()
        requested_language = "Hebrew" if language == "he" else "English"
        return (
            "You are JARVIS, the user's private desktop AI assistant. You are an agent, not a command matcher. "
            "Understand the user's intent from normal language and prior conversation. Resolve pronouns and follow-ups from the chat history. "
            f"Your tone is {tone}; address the user as '{address}' naturally. Keep answers {verbosity}. "
            f"Reply in {requested_language} in gui_text. spoken_text should be a short natural English voice reply for the current TTS setup. "
            "Use tools when they are actually needed. Mentioning a topic must NEVER cause an app/site to open. "
            "Only open, close, show, launch, navigate, lock, or otherwise change the user's UI when the user explicitly asks for that action. "
            "If an app/site could help but was not requested, offer it briefly instead of opening it. "
            "Use answer_web_question for public facts/current information that benefit from internet research. "
            "Use get_weather for weather instead of generic web search whenever possible. "
            "Use calendar_list_events for the user's personal schedule and calendar_status/calendar_connect for Google Calendar access; never replace personal calendar data with public web search. "
            "Use get_daily_briefing when the user asks for their briefing, what they missed, today's update, sports/news roundup, or a refresh of the daily intelligence feed. "
            "Use f1_next_lesson when the user asks to learn something new about Formula 1, and teach from that progression instead of repeating the same basics. "
            "For exhaustive, historical, list, range, season, tournament, or 'all/since/from/back to YEAR' requests, use answer_web_question and fulfill the whole requested range from the returned evidence. Do not silently shorten the request to a few examples. If evidence is incomplete, say exactly which portion you could not verify. "
            "Never substitute public web search for private data such as the user's schedule, calendar, inbox, private messages, or reminders. "
            "When answer_web_question returns sources, synthesize the evidence into a clean answer or table; never dump raw evidence/HTML. Include a short Sources section in gui_text, but do not read URLs aloud in spoken_text. "
            "The JARVIS workspace itself is controllable through ui_show_panel, ui_hide_panel, ui_switch_workspace, ui_open_surface, and ui_hololab_config. Custom saved workspace names are valid. When the user explicitly asks to bring a normal website/domain into the JARVIS layout, use ui_open_surface; do not force games or sensitive desktop apps into an embedded panel. When the user asks to create or modify a HoloLab prototype, use ui_hololab_config with the requested shape, material, and dimensions. Use UI tools only when the user explicitly asks to change what the interface shows. "
            "When the user explicitly asks what you can see, whether you can see them, or asks you to inspect the enabled camera, call analyze_camera. Never claim camera vision without that tool result. "
            "If a capability is unavailable, say so plainly rather than inventing access. "
            "You have no raw shell access. Use only the provided tools. "
            "After all required tool calls finish, return ONLY a compact JSON object with keys intent, gui_text, spoken_text. "
            "Do not put markdown fences around the JSON."
        )

    @staticmethod
    def _assistant_message_for_history(message: dict[str, Any]) -> dict[str, Any]:
        kept: dict[str, Any] = {"role": "assistant"}
        if message.get("content") is not None:
            kept["content"] = message.get("content")
        if message.get("tool_calls"):
            kept["tool_calls"] = message.get("tool_calls")
        return kept

    @staticmethod
    def _parse_tool_call(call: Any) -> tuple[str, str, dict[str, Any]]:
        if not isinstance(call, dict):
            raise ProviderError(f"Invalid tool call: {call!r}")
        tool_call_id = str(call.get("id") or "tool_call")
        function = call.get("function") or {}
        name = str(function.get("name") or "").strip()
        if not name:
            raise ProviderError("Model requested a tool without a name.")
        raw_args = function.get("arguments", {})
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {}
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            args = {}
        return tool_call_id, name, args

    def _parse_final_response(self, content: str, language: str) -> dict[str, str]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            gui = cleaned
            return {"intent": "chat", "gui_text": gui, "spoken_text": self._spoken_from_gui(gui)}
        if not isinstance(payload, dict):
            gui = cleaned
            return {"intent": "chat", "gui_text": gui, "spoken_text": self._spoken_from_gui(gui)}
        gui = str(payload.get("gui_text") or payload.get("answer") or "").strip()
        spoken = str(payload.get("spoken_text") or "").strip() or self._spoken_from_gui(gui)
        intent = str(payload.get("intent") or "chat").strip()
        if not gui:
            gui = "I completed that." if language == "en" else "סיימתי את זה."
        return {"intent": intent, "gui_text": gui, "spoken_text": spoken}

    @staticmethod
    def _spoken_from_gui(gui: str) -> str:
        text = re.sub(r"\n+Sources:.*$", "", gui, flags=re.IGNORECASE | re.DOTALL).strip()
        text = re.sub(r"\s+", " ", text)
        return text[:240] if text else "Done."

    def _ensure_address(self, text: str, language: str) -> str:
        if self.config.tone_mode != "Respectful":
            return text
        address = (self.config.address_name or "sir").strip()
        if not address or text.lower().startswith(address.lower()):
            return text
        prefix = address.capitalize() if language == "en" else address
        return f"{prefix}, {text}"
