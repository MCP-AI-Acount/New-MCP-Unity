using System;
using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.SceneManagement;

public static class RemoteAutomation
{
    [Serializable]
    private class TaskPayload
    {
        public string sceneName;
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
