# LoginPanel 프리팹 구조

## 권장 계층

- `Canvas`
  - `LoginPanel` (Image)
    - `TitleText` (TMP_Text)
    - `EmailInput` (TMP_InputField)
    - `PasswordInput` (TMP_InputField)
    - `LoginButton` (Button + TMP_Text)
    - `StatusText` (TMP_Text)
    - `ApiLoginClient` (Empty GameObject + `ApiLoginClient`)
    - `LoginPanelController` (`LoginPanelController`)

## 인스펙터 연결

- `LoginPanelController.emailInput` -> `EmailInput`
- `LoginPanelController.passwordInput` -> `PasswordInput`
- `LoginPanelController.loginButton` -> `LoginButton`
- `LoginPanelController.statusText` -> `StatusText`
- `LoginPanelController.apiLoginClient` -> `ApiLoginClient`

## API 연동

- `ApiLoginClient.loginApiUrl` 에 Firebase Auth Gateway 또는 자체 로그인 API 주소 입력
- `ApiLoginClient.n8nWebhookUrl` 에 n8n Webhook URL 입력

## Firebase 선택 시

- Firebase Auth REST API 를 사용할 경우, 서버에서 토큰 검증 후 사용자 프로필 반환하도록 구성
- 클라이언트에는 최소 정보(`idToken`, `userId`)만 전달
