# FANBOX 支援者一覧の自動更新

FANBOXの「ファン一覧」から現在の支援者名を取得し、`PatronName.txt` に変更がある時だけGitHubへ送信します。

## 初回セットアップ

1. PowerShellでこのフォルダを開き、`powershell -ExecutionPolicy Bypass -File .\setup.ps1` を実行します。
2. `setup_login.bat` を実行します。
3. 表示された専用Chromeでpixiv/FANBOXへログインします。取得が完了するとChromeは自動で閉じます。
4. `powershell -ExecutionPolicy Bypass -File .\register_daily_task.ps1` を実行します。

既定では毎日9:00に実行します。時刻を変える場合は、たとえば18:30なら次のように登録します。

```powershell
powershell -ExecutionPolicy Bypass -File .\register_daily_task.ps1 -At 18:30
```

PCが時刻に起動していなかった場合は、次に利用可能になった時に実行されます。ログイン状態は普段使いのChromeとは分離し、`%LOCALAPPDATA%\FanboxSupporterUpdater\ChromeProfile` に保存します。

## 手動実行

`upload_git.bat` を実行します。ログは `%LOCALAPPDATA%\FanboxSupporterUpdater\logs\update.log` に残ります。

FANBOXのログイン期限が切れた場合は `setup_login.bat` をもう一度実行してください。取得に失敗した時は `PatronName.txt` を上書きせず、GitHubにも送信しません。
