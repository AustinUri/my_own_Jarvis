"""Exercise the deployed dashboard with a real Qt Chromium renderer and synthetic chat."""
import functools
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch


@unittest.skipUnless(os.getenv("JARVIS_TEST_WEBENGINE") == "1", "Enable with JARVIS_TEST_WEBENGINE=1 in a desktop session")
class DashboardFrameTests(unittest.TestCase):
    def test_chat_transport_and_composer(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineCore import QWebEngineScript
        from PySide6.QtWidgets import QApplication
        from workspace.private_dashboard import DashboardPage, ConversationHandler, SCHEME
        from workspace.integrated_shell import JarvisIntegratedShell

        root = Path(__file__).resolve().parents[1]
        class LocalFiles(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                if self.path.startswith("/api/"):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"{}")
                else:
                    super().do_GET()

        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(LocalFiles, directory=root/"workspace_ui"/"dist"))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        app = QApplication.instance() or QApplication([])
        brain = Mock()
        brain.memory.collections.return_value = ["", "Garden"]
        brain.memory.list_conversations.return_value = []
        brain.status.return_value = dict(active="Qwen",error="",connected=False,fallback=True,model="",
                                         models=[],enabled=False,remember=False,cost_confirmed=False)
        ask = Mock(return_value="Synthetic private answer")
        url = f"http://127.0.0.1:{server.server_port}/?build=29.2"
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        with patch("workspace.integrated_shell.QStandardPaths.writableLocation", return_value=directory.name):
            shell = JarvisIntegratedShell(url, brain_factory=lambda: brain, ask_private=ask)
        self.addCleanup(shell.close)
        page = shell.control_view.page()
        profile = page.profile()
        self.assertIsInstance(page, DashboardPage)
        self.assertIsInstance(profile.urlSchemeHandler(SCHEME), ConversationHandler)
        self.assertIsNone(shell.surface_profile.urlSchemeHandler(SCHEME))
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(profile.isOffTheRecord() or bool(profile.persistentStoragePath()))
            instrument = QWebEngineScript()
            instrument.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            instrument.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            instrument.setRunsOnSubFrames(False)
            instrument.setSourceCode("window.sent=[]; window.WebSocket=class{constructor(){this.readyState=1; window.testWS=this}send(s){sent.push(s)}}")
            page.scripts().insert(instrument)
            shell.resize(1280, 840)
            shell.show()
            shell.control_view.reload()

            def until(fn):
                end = time.monotonic() + 10
                while time.monotonic() < end:
                    app.processEvents()
                    value = fn()
                    if value:
                        return value
                    time.sleep(.01)
                self.fail("Timed out waiting for desktop DOM or private response")

            def js(script, frame=None):
                values = []
                (frame or page.mainFrame()).runJavaScript(script, 0, values.append)
                until(lambda: bool(values))
                return values[0]

            until(lambda: js("!!document.querySelector('.composer input') && !!window.testWS"))
            result = js("""(()=>{const input=document.querySelector('.composer input');input.value='draft';
                let replacements=0; const t=performance.now();
                for(let i=0;i<30;i++){testWS.onmessage({data:JSON.stringify({type:'response',payload:{text:'Update'}})});
                if(input!==document.querySelector('.composer input')) replacements++}
                return JSON.stringify({replacements,draft:document.querySelector('.composer input').value,ms:performance.now()-t})})()""")
            measurements = json.loads(result)
            self.assertEqual(measurements["replacements"], 0)
            self.assertEqual(measurements["draft"], "draft")
            js("document.querySelector('.conversation form').requestSubmit()")
            self.assertIn("draft", js("JSON.stringify(sent)"))
            js("""const mode=document.querySelector('[aria-label="Conversation mode"]');
                mode.value='Private';mode.dispatchEvent(new Event('change'))""")
            frame = until(lambda: next((f for f in page.mainFrame().children()
                                        if f.url().scheme()=="jarvis-chat"), None))
            self.assertTrue(js("document.querySelector('.private-conversation').contentDocument===null"))
            until(lambda: js("document.querySelector('#project')?.options.length===2", frame)
                  or js("document.querySelector('#status')?.textContent?.startsWith('Open the native')", frame))
            self.assertEqual(js("document.querySelector('#project').options.length", frame), 2,
                             js("document.querySelector('#status').textContent", frame))
            js("""document.querySelector('#project').value='Garden';
                document.querySelector('#question').value='Synthetic private question';
                document.querySelector('#compose').requestSubmit()""", frame)
            until(lambda: js("document.querySelector('#history').textContent.includes('Synthetic private answer')", frame))
            ask.assert_called_once_with("Garden", "Synthetic private question")
            self.assertNotIn("Synthetic private", js("JSON.stringify(sent)+document.body.innerText+JSON.stringify(localStorage)"))
            self.assertEqual(js("JSON.stringify(localStorage)", frame), "{}")
            self.assertEqual(js("JSON.stringify(sessionStorage)", frame), "{}")
            js("""fetch('jarvis-chat://desktop/state',{method:'POST',body:'{}'}).then(()=>window.probe='open').catch(()=>window.probe='closed')""")
            until(lambda: js("!!window.probe"))
            self.assertEqual(js("window.probe"),"closed")
            self.assertFalse(page.acceptNavigationRequest(QUrl("http://localhost:1234/"), None, True))
            self.assertFalse(page.acceptNavigationRequest(QUrl("https://example.invalid/"), None, False))
            js("document.querySelector('#memory').click()", frame)
            until(lambda: shell._private_dock and shell._private_dock.isVisible())
            self.assertEqual(shell._private_ai_dialog.project.currentData(), "Garden")
            self.assertEqual(shell._private_ai_dialog.tabs.currentIndex(), 2)
            shell._private_dock.hide()
            js("document.querySelector('#providers').click()", frame)
            until(lambda: shell._private_dock.isVisible())
            self.assertEqual(shell._private_ai_dialog.tabs.currentIndex(), 1)
            shell._private_dock.hide()
            if os.getenv("JARVIS_DASHBOARD_SCREENSHOT"):
                js("document.querySelector('.private-conversation').scrollIntoView({block:'center'})")
                app.processEvents()
                self.assertTrue(shell.grab().save(os.environ["JARVIS_DASHBOARD_SCREENSHOT"]))
            js("""const mode=document.querySelector('[aria-label="Conversation mode"]');
                mode.value='Shared';mode.dispatchEvent(new Event('change'))""")
            until(lambda: js("!!document.querySelector('.conversation .composer input')"))
            self.assertNotIn("Synthetic private", js("document.body.innerText"))
