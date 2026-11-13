# FPS将棋

将棋盤で相手の駒を取りに行くと、両者がその駒を一人称視点で操作して決闘します。相手の王を決闘で倒すと勝利です。9×9の通常対局と、各6枚の駒を使う5×5の「5五将棋」が遊べます。

5五将棋では、駒の配置・持ち駒・手番が同じ局面が4回現れると先手が負けます。連続王手による千日手は、王手を続けた側の負けです。

## Windows版で遊ぶ

1. [最新のWindows版（ZIP）をダウンロード](https://github.com/dugite-git/FPSshogi-Releases/releases/latest/download/FPSshogi-Windows.zip)し、すべて展開します。
2. 展開先の `FPSshogi.exe` を起動します。

- **1台のPCで2人対戦**　タイトルの「オフライン」から対戦準備に進みます。コントローラー2台、またはキーボード・マウスとコントローラー1台で参加できます。A／Enterで参加し、一度離してからもう一度押して準備完了にします。1Pがモードを選び、両者の準備後にSTART／F5で開始します。
- **Steamでフレンドと対戦**　2人ともSteamにサインインして同じ版を起動します。ホストはタイトルの「オンライン」から部屋を作って相手を招待します。準備画面でホストがモードを選び、双方が準備完了にした後でホストが開始します。ゲームより後にSteamを起動した場合も、Steamがオンラインになってからゲーム内で部屋を作れます。

ひとりで駒を試すには、タイトルの「練習場」を選んでください。[最新リリースの変更点](https://github.com/dugite-git/FPSshogi-Releases/releases/latest)も確認できます。

## テスターの投稿・質問

[**不具合報告・感想・改善案を投稿する（Discussions）**](https://github.com/dugite-git/FPSshogi-Releases/discussions)  
[はじめに：投稿方法とカテゴリーの選び方](https://github.com/dugite-git/FPSshogi-Releases/discussions/1)

GitHubにログインすれば、どなたでも投稿・返信できます。参加申請は不要です。上の案内と下のリンクから開くと、本文に日本語の記入項目が入ります。不要な任意項目は削除して構いません。

| 投稿したい内容 | 投稿先 |
| --- | --- |
| 不具合報告 | [不具合報告](https://github.com/dugite-git/FPSshogi-Releases/discussions/new?category=%E4%B8%8D%E5%85%B7%E5%90%88%E5%A0%B1%E5%91%8A&title=%5B%E4%B8%8D%E5%85%B7%E5%90%88%5D%20&body=%23%23%23%20%E9%81%8A%E3%82%93%E3%81%A0%E3%83%90%E3%83%BC%E3%82%B8%E3%83%A7%E3%83%B3%0A%EF%BC%88%E4%B8%8D%E6%98%8E%E3%81%AA%E3%82%89%E3%80%8C%E4%B8%8D%E6%98%8E%E3%80%8D%E3%81%A8%E8%A8%98%E5%85%A5%E3%81%97%E3%81%A6%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84%EF%BC%89%0A%0A%23%23%23%20%E8%B5%B7%E3%81%8D%E3%81%9F%E3%81%93%E3%81%A8%0A%0A%0A%23%23%23%20%E5%86%8D%E7%8F%BE%E6%89%8B%E9%A0%86%E3%83%BB%E6%9C%AC%E6%9D%A5%E3%81%A9%E3%81%86%E3%81%AA%E3%82%8B%E3%81%A8%E6%80%9D%E3%81%A3%E3%81%9F%E3%81%8B%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A%0A%23%23%23%20%E3%83%A2%E3%83%BC%E3%83%89%E3%83%BB%E9%A7%92%E3%83%BB%E6%93%8D%E4%BD%9C%E6%A9%9F%E5%99%A8%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A%0A%23%23%23%20%E7%94%BB%E5%83%8F%E3%83%BB%E5%8B%95%E7%94%BB%E3%83%BB%E8%A3%9C%E8%B6%B3%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A) |
| 感想・バランス | [感想・バランス](https://github.com/dugite-git/FPSshogi-Releases/discussions/new?category=%E6%84%9F%E6%83%B3-%E3%83%90%E3%83%A9%E3%83%B3%E3%82%B9&title=%5B%E6%84%9F%E6%83%B3%E3%83%BB%E3%83%90%E3%83%A9%E3%83%B3%E3%82%B9%5D%20&body=%23%23%23%20%E9%81%8A%E3%82%93%E3%81%A0%E6%84%9F%E6%83%B3%0A%EF%BC%88%E4%B8%80%E8%A8%80%E3%81%A7%E3%82%82%E5%A4%A7%E4%B8%88%E5%A4%AB%E3%81%A7%E3%81%99%EF%BC%89%0A%0A%23%23%23%20%E3%83%90%E3%83%BC%E3%82%B8%E3%83%A7%E3%83%B3%E3%83%BB%E9%A7%92%E3%83%BB%E3%83%A2%E3%83%BC%E3%83%89%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A%0A%23%23%23%20%E3%81%9D%E3%81%86%E6%84%9F%E3%81%98%E3%81%9F%E5%A0%B4%E9%9D%A2%E3%83%BB%E7%94%BB%E5%83%8F%E3%82%84%E5%8B%95%E7%94%BB%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A) |
| 改善案 | [改善案](https://github.com/dugite-git/FPSshogi-Releases/discussions/new?category=%E6%94%B9%E5%96%84%E6%A1%88&title=%5B%E6%94%B9%E5%96%84%E6%A1%88%5D%20&body=%23%23%23%20%E4%B8%8D%E4%BE%BF%E3%81%AA%E3%81%93%E3%81%A8%E3%83%BB%E3%81%93%E3%81%86%E3%81%AA%E3%81%A3%E3%81%A6%E3%81%BB%E3%81%97%E3%81%84%E3%81%93%E3%81%A8%0A%0A%0A%23%23%23%20%E6%94%B9%E5%96%84%E6%A1%88%E3%82%84%E5%8F%82%E8%80%83%E4%BE%8B%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A%0A%23%23%23%20%E9%96%A2%E4%BF%82%E3%81%99%E3%82%8B%E7%94%BB%E9%9D%A2%E3%83%BB%E9%A7%92%E3%83%BB%E3%83%90%E3%83%BC%E3%82%B8%E3%83%A7%E3%83%B3%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A) |
| 操作・起動・ルールなどの質問 | [質問](https://github.com/dugite-git/FPSshogi-Releases/discussions/new?category=%E8%B3%AA%E5%95%8F&title=%5B%E8%B3%AA%E5%95%8F%5D%20&body=%23%23%23%20%E8%B3%AA%E5%95%8F%E3%81%97%E3%81%9F%E3%81%84%E3%81%93%E3%81%A8%0A%0A%0A%23%23%23%20%E3%83%90%E3%83%BC%E3%82%B8%E3%83%A7%E3%83%B3%E3%83%BB%E3%83%A2%E3%83%BC%E3%83%89%E3%83%BB%E6%93%8D%E4%BD%9C%E6%A9%9F%E5%99%A8%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A%0A%23%23%23%20%E8%A9%A6%E3%81%97%E3%81%9F%E3%81%93%E3%81%A8%E3%83%BB%E8%A1%A8%E7%A4%BA%E3%81%95%E3%82%8C%E3%81%9F%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8%EF%BC%88%E4%BB%BB%E6%84%8F%EF%BC%89%0A%0A) |

不具合は遊んだバージョンと症状を記入してください。手順や画像・動画は、分かる範囲で添えれば大丈夫です。短い感想も歓迎します。
