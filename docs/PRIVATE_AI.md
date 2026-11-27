# Private AI in the JARVIS Control Center

Open the Windows Control Center and select **Private** in the **Conversation** widget. Choose **Personal** or a named project from **Collection**. The Windows account running the desktop app identifies the local user. Shared chat, voice, Skill Fabric actions and Android requests use their existing routes.

## Connect and verify ChatGPT

1. From this checkout, run `.\.venv\Scripts\python.exe main.py` in PowerShell. Open **Conversation → Private → Providers** in the Control Center. The **Private AI** entry in the JARVIS tray menu also opens provider settings.
2. Select **Connect with ChatGPT**, select your personal Plus or Pro workspace in the system browser and authorize use of your plan. Return to JARVIS and select a model from the account's list. **Refresh models** repeats discovery. The OpenAI preview explicitly includes personal projects running locally. OpenAI determines the permissions for the selected account and workspace. [Official integration guide](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)
3. Open **Manage ChatGPT usage**. In ChatGPT Settings → Usage, check the saved credit setting. A JARVIS weekly app limit below 100% prevents credit use for this app. Alternatively, verify that credit use for apps is switched off. If you cannot verify either control, keep plan inference disabled. JARVIS has no documented way to read these settings or to enforce a per-request credit cap. [OpenAI usage controls](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites)
4. In JARVIS, check **I verified my ChatGPT credit settings**, confirm, then check **Use ChatGPT as the preferred provider**. Reconfirm after restarting JARVIS, reconnecting or changing the account's usage settings. Disable the provider before changing a control that protects against credit use.
5. Select **Test ChatGPT plan inference**. The test asks for the word READY with an empty memory context. Its answer appears only after OpenAI reports a completed response. A connected status and a populated model list verify login and model discovery. The smoke button uses only ChatGPT, so a local model cannot supply a false positive.

With local fallback enabled, ordinary private questions try ChatGPT when available, followed by Qwen and Gemma through LM Studio on loopback. The panel shows which provider supplied the last answer and any fallback reason. A plan limit pauses future plan requests. Check the reset or saved app limit under Usage before reconnecting and re-enabling it. The fallback reads the existing local model configuration, gaming guard and concurrency limit. LM Studio must advertise the model on its local server.

## Import selected memory

1. Choose **Personal** or a named project using **New collection**.
2. In **Memory**, select **Import ChatGPT conversations** and choose the export ZIP or conversations JSON. The preview shows titles and starts with an empty selection. No content is stored at this stage.
3. Select individual conversations. For an entire project, choose a named destination and a project explicitly identified in the export. Conversations without reliable membership can be assigned individually. Review the count and destination, then confirm that every selected conversation belongs to you.
4. Use **Review** or **Delete conversation** within the active collection. **Export all my memory** and **Delete all my memory** apply across the signed-in OS user's collections. Export writes a new plaintext JSON file, so choose a private local destination. **Save new questions and answers** is off by default.

A changed source must be previewed again. Reimport updates selected conversation IDs in the destination collection. Visible text comes from the active branch. Archived branches, tool output, attachments and project files are excluded. Missing conversations in a later export do not trigger deletion. Project membership currently requires an unambiguous conversation-level `project_id`.

## Storage and privacy

The private memory database and provider settings live in the user's local application data directory. On Windows this is normally `%LOCALAPPDATA%\Jarvis\private-ai`. OAuth token bundles are encrypted with a key held by the native OS credential vault. The Windows key stays in local-machine Credential Manager under the current user. The private memory SQLite database relies on OS profile access controls. People sharing a single OS login share its memory identity and its one linked ChatGPT registration.

Each question can retrieve up to three relevant excerpts of 420 characters from its own user and collection. Enabling ChatGPT sends the question and those excerpts to OpenAI. With local-only routing, the same excerpts stay on loopback. OAuth sign-in provides no access to ChatGPT history. The complete export, imported collection, and OAuth credentials are never synchronized to the phone or Oracle.

The provider uses OIDC authorization code with S256 PKCE, a loopback callback, state, nonce and OpenAI's signed identity tokens. Plan requests use the OAuth access token at the documented Responses endpoint with `store: false` and `stream: true`. Disconnect removes renewable credentials locally and attempts remote revocation. If that fails, open ChatGPT Settings → Security and login → Login connections to revoke JARVIS. [OpenAI session lifecycle](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions) · [Responses contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
