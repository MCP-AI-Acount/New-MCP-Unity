using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class LoginPanelController : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private TMP_InputField emailInput;
    [SerializeField] private TMP_InputField passwordInput;
    [SerializeField] private Button loginButton;
    [SerializeField] private TMP_Text statusText;

    [Header("Dependencies")]
    [SerializeField] private ApiLoginClient apiLoginClient;

    private void Awake()
    {
        loginButton.onClick.AddListener(OnClickLogin);
        statusText.text = "로그인 필요";
    }

    private void OnDestroy()
    {
        loginButton.onClick.RemoveListener(OnClickLogin);
    }

    private void OnClickLogin()
    {
        var email = emailInput.text.Trim();
        var password = passwordInput.text;
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
        {
            statusText.text = "이메일/비밀번호를 입력하세요.";
            return;
        }

        statusText.text = "로그인 시도 중...";
        apiLoginClient.RequestLogin(email, password, OnLoginDone);
    }

    private void OnLoginDone(LoginResponseBody result)
    {
        if (result != null && result.success)
        {
            statusText.text = "로그인 성공: " + result.userId;
            return;
        }
        statusText.text = "로그인 실패: " + (result == null ? "응답 없음" : result.message);
    }
}
