using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class LoginRequestBody
{
    public string email;
    public string password;
}

[Serializable]
public class LoginResponseBody
{
    public bool success;
    public string userId;
    public string idToken;
    public string message;
}

public class ApiLoginClient : MonoBehaviour
{
    [SerializeField] private string loginApiUrl = "https://YOUR_API_URL/login";
    [SerializeField] private string n8nWebhookUrl = "https://YOUR_N8N_WEBHOOK_URL";

    public void RequestLogin(string email, string password, Action<LoginResponseBody> onDone)
    {
        StartCoroutine(RequestLoginCoroutine(email, password, onDone));
    }

    private IEnumerator RequestLoginCoroutine(string email, string password, Action<LoginResponseBody> onDone)
    {
        var reqBody = new LoginRequestBody
        {
            email = email,
            password = password,
        };
        var json = JsonUtility.ToJson(reqBody);
        var req = new UnityWebRequest(loginApiUrl, "POST");
        var data = Encoding.UTF8.GetBytes(json);
        req.uploadHandler = new UploadHandlerRaw(data);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();

        LoginResponseBody result = new LoginResponseBody();
        if (req.result == UnityWebRequest.Result.Success)
        {
            result = JsonUtility.FromJson<LoginResponseBody>(req.downloadHandler.text);
        }
        else
        {
            result.success = false;
            result.message = req.error;
        }

        StartCoroutine(PostLoginLogToN8N(email, result.success, result.message));
        onDone?.Invoke(result);
    }

    private IEnumerator PostLoginLogToN8N(string email, bool success, string message)
    {
        if (string.IsNullOrWhiteSpace(n8nWebhookUrl))
        {
            yield break;
        }
        string body = "{\"event\":\"unity_login\",\"email\":\"" + email + "\",\"success\":" + (success ? "true" : "false") + ",\"message\":\"" + EscapeJson(message) + "\"}";
        var req = new UnityWebRequest(n8nWebhookUrl, "POST");
        var data = Encoding.UTF8.GetBytes(body);
        req.uploadHandler = new UploadHandlerRaw(data);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();
    }

    private string EscapeJson(string input)
    {
        if (string.IsNullOrEmpty(input))
        {
            return "";
        }
        return input.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
