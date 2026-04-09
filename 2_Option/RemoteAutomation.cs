using System;
using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public static class RemoteAutomation
{
    [Serializable]
    private class TaskPayload
    {
        public string sceneName;
        public string scene;
        public string canvasName;
        public string graphName;
        public string colorHex;
        public string screenshotPath;
        public string uploadUrl;
        public string webhookUrl;
        public string requestId;
    }

    [Serializable]
    private class LogBody
    {
        public string requestId;
        public bool success;
        public string message;
        public string screenshotPath;
    }

    // Unity Worker에서 -executeMethod 로 호출
    // 예시:
    // -executeMethod RemoteAutomation.EntryPoint --taskType=play_and_capture --taskPayload={"sceneName":"SampleScene","screenshotPath":"/tmp/play.png","uploadUrl":"","webhookUrl":"https://your-n8n-webhook","requestId":"req-1"}
    public static void EntryPoint()
    {
        string taskType = GetArgValue("--taskType=");
        string taskPayloadJson = GetArgValue("--taskPayload=");
        if (string.IsNullOrWhiteSpace(taskType))
        {
            Debug.LogError("[RemoteAutomation] --taskType is required");
            return;
        }
        if (string.IsNullOrWhiteSpace(taskPayloadJson))
        {
            Debug.LogError("[RemoteAutomation] --taskPayload is required");
            return;
        }

        TaskPayload payload;
        try
        {
            payload = JsonUtility.FromJson<TaskPayload>(taskPayloadJson);
        }
        catch (Exception e)
        {
            Debug.LogError("[RemoteAutomation] task payload parse error: " + e.Message);
            return;
        }

        if (taskType == "play_and_capture")
        {
            RunPlayAndCapture(payload);
            return;
        }

        if (taskType == "set_canvas_graph_horizontal_green" || taskType == "ui_set_graph_horizontal_green")
        {
            RunSetCanvasGraphHorizontalGreen(payload);
            return;
        }

        Debug.LogWarning("[RemoteAutomation] unsupported taskType: " + taskType);
    }

    private static void RunPlayAndCapture(TaskPayload payload)
    {
        string sceneName = string.IsNullOrWhiteSpace(payload.sceneName) ? SceneManager.GetActiveScene().name : payload.sceneName;
        string screenshotPath = string.IsNullOrWhiteSpace(payload.screenshotPath) ? "/tmp/unity-play-capture.png" : payload.screenshotPath;

        try
        {
            if (!string.IsNullOrWhiteSpace(sceneName))
            {
                SceneManager.LoadScene(sceneName);
            }

            ScreenCapture.CaptureScreenshot(screenshotPath);
            Debug.Log("[RemoteAutomation] screenshot captured: " + screenshotPath);

            if (!string.IsNullOrWhiteSpace(payload.uploadUrl))
            {
                UploadScreenshot(payload.uploadUrl, screenshotPath);
            }

            if (!string.IsNullOrWhiteSpace(payload.webhookUrl))
            {
                SendWebhook(payload.webhookUrl, payload.requestId, true, "play_and_capture done", screenshotPath);
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[RemoteAutomation] play_and_capture error: " + e.Message);
            if (!string.IsNullOrWhiteSpace(payload.webhookUrl))
            {
                SendWebhook(payload.webhookUrl, payload.requestId, false, e.Message, screenshotPath);
            }
        }
    }

    private static void UploadScreenshot(string uploadUrl, string filePath)
    {
        if (!File.Exists(filePath))
        {
            Debug.LogError("[RemoteAutomation] screenshot file not found: " + filePath);
            return;
        }

        byte[] bytes = File.ReadAllBytes(filePath);
        WWWForm form = new WWWForm();
        form.AddBinaryData("file", bytes, Path.GetFileName(filePath), "image/png");

        using (UnityWebRequest req = UnityWebRequest.Post(uploadUrl, form))
        {
            var op = req.SendWebRequest();
            while (!op.isDone) { }
            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError("[RemoteAutomation] upload failed: " + req.error);
                return;
            }
            Debug.Log("[RemoteAutomation] upload success");
        }
    }

    private static void RunSetCanvasGraphHorizontalGreen(TaskPayload payload)
    {
        string sceneName = string.IsNullOrWhiteSpace(payload.sceneName) ? payload.scene : payload.sceneName;
        string canvasName = string.IsNullOrWhiteSpace(payload.canvasName) ? "Canvas" : payload.canvasName;
        string graphName = string.IsNullOrWhiteSpace(payload.graphName) ? "Graph" : payload.graphName;
        string colorHex = string.IsNullOrWhiteSpace(payload.colorHex) ? "#00FF00" : payload.colorHex;
        Color graphColor = ParseColorOrDefault(colorHex, new Color(0f, 1f, 0f, 1f));

        try
        {
            if (!string.IsNullOrWhiteSpace(sceneName))
            {
                SceneManager.LoadScene(sceneName);
            }

            Transform canvasTransform = FindCanvasTransform(canvasName);
            if (canvasTransform == null)
            {
                throw new Exception("Canvas not found: " + canvasName);
            }

            int changedCount = 0;
            Transform target = FindDescendantByName(canvasTransform, graphName);
            if (target != null)
            {
                ApplyGraphStyle(target, graphColor);
                changedCount++;
            }
            else
            {
                foreach (Transform t in canvasTransform.GetComponentsInChildren<Transform>(true))
                {
                    if (t.name.IndexOf("graph", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        ApplyGraphStyle(t, graphColor);
                        changedCount++;
                    }
                }
            }

            if (changedCount == 0)
            {
                throw new Exception("Graph object not found under canvas: " + canvasName);
            }

            SaveActiveSceneIfEditor();
            Debug.Log("[RemoteAutomation] graph style updated. changedCount=" + changedCount);

            if (!string.IsNullOrWhiteSpace(payload.webhookUrl))
            {
                SendWebhook(payload.webhookUrl, payload.requestId, true, "set_canvas_graph_horizontal_green done", "");
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[RemoteAutomation] set_canvas_graph_horizontal_green error: " + e.Message);
            if (!string.IsNullOrWhiteSpace(payload.webhookUrl))
            {
                SendWebhook(payload.webhookUrl, payload.requestId, false, e.Message, "");
            }
        }
    }

    private static Transform FindCanvasTransform(string canvasName)
    {
        Scene scene = SceneManager.GetActiveScene();
        GameObject[] roots = scene.GetRootGameObjects();
        for (int i = 0; i < roots.Length; i++)
        {
            Canvas rootCanvas = roots[i].GetComponent<Canvas>();
            if (rootCanvas != null && string.Equals(roots[i].name, canvasName, StringComparison.OrdinalIgnoreCase))
            {
                return roots[i].transform;
            }
        }

        for (int i = 0; i < roots.Length; i++)
        {
            Canvas[] canvases = roots[i].GetComponentsInChildren<Canvas>(true);
            for (int j = 0; j < canvases.Length; j++)
            {
                if (string.Equals(canvases[j].name, canvasName, StringComparison.OrdinalIgnoreCase))
                {
                    return canvases[j].transform;
                }
            }
        }

        for (int i = 0; i < roots.Length; i++)
        {
            Canvas[] canvases = roots[i].GetComponentsInChildren<Canvas>(true);
            if (canvases.Length > 0)
            {
                return canvases[0].transform;
            }
        }

        return null;
    }

    private static Transform FindDescendantByName(Transform root, string name)
    {
        if (root == null)
        {
            return null;
        }

        foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
        {
            if (string.Equals(t.name, name, StringComparison.OrdinalIgnoreCase))
            {
                return t;
            }
        }
        return null;
    }

    private static void ApplyGraphStyle(Transform target, Color graphColor)
    {
        RectTransform rt = target.GetComponent<RectTransform>();
        if (rt != null)
        {
            Vector2 size = rt.sizeDelta;
            float width = Mathf.Abs(size.x);
            float height = Mathf.Abs(size.y);
            if (width < 1f && height < 1f)
            {
                rt.sizeDelta = new Vector2(640f, 220f);
            }
            else if (width < height)
            {
                rt.sizeDelta = new Vector2(height, width);
            }
        }

        Slider slider = target.GetComponent<Slider>();
        if (slider != null)
        {
            slider.direction = Slider.Direction.LeftToRight;
        }

        ScrollRect scrollRect = target.GetComponent<ScrollRect>();
        if (scrollRect != null)
        {
            scrollRect.horizontal = true;
            scrollRect.vertical = false;
        }

        Graphic[] graphics = target.GetComponentsInChildren<Graphic>(true);
        for (int i = 0; i < graphics.Length; i++)
        {
            graphics[i].color = graphColor;
        }
    }

    private static Color ParseColorOrDefault(string hex, Color fallback)
    {
        if (string.IsNullOrWhiteSpace(hex))
        {
            return fallback;
        }

        Color parsed;
        if (ColorUtility.TryParseHtmlString(hex, out parsed))
        {
            return parsed;
        }

        if (!hex.StartsWith("#") && ColorUtility.TryParseHtmlString("#" + hex, out parsed))
        {
            return parsed;
        }

        return fallback;
    }

    private static void SaveActiveSceneIfEditor()
    {
#if UNITY_EDITOR
        Scene active = SceneManager.GetActiveScene();
        if (active.IsValid())
        {
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(active);
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(active);
        }
#endif
    }

    private static void SendWebhook(string webhookUrl, string requestId, bool success, string message, string screenshotPath)
    {
        LogBody body = new LogBody
        {
            requestId = requestId,
            success = success,
            message = message,
            screenshotPath = screenshotPath
        };
        string json = JsonUtility.ToJson(body);
        byte[] data = Encoding.UTF8.GetBytes(json);

        using (UnityWebRequest req = new UnityWebRequest(webhookUrl, "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(data);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            var op = req.SendWebRequest();
            while (!op.isDone) { }
            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError("[RemoteAutomation] webhook failed: " + req.error);
                return;
            }
            Debug.Log("[RemoteAutomation] webhook success");
        }
    }

    private static string GetArgValue(string prefix)
    {
        string[] args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i].StartsWith(prefix, StringComparison.Ordinal))
            {
                return args[i].Substring(prefix.Length);
            }
        }
        return "";
    }
}
