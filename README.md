# FinalDatabase
<img width="1036" height="543" alt="image" src="https://github.com/user-attachments/assets/b45956b0-d01f-4a8e-a462-350f2f751b76" />

<img width="1051" height="597" alt="image" src="https://github.com/user-attachments/assets/90897df8-ca9b-4700-a0ff-7b91d61239eb" />

### 系統開發方法及工具

<img width="1055" height="595" alt="image" src="https://github.com/user-attachments/assets/9d3a9fc0-9e7d-4997-b432-f38a803194a0" />

<img width="967" height="592" alt="image" src="https://github.com/user-attachments/assets/4a07245b-1a06-4970-9da3-502465a532dc" />

<img width="1013" height="599" alt="image" src="https://github.com/user-attachments/assets/6f769450-2a20-4325-a0bd-e2a50e658f1d" />


### 結果


- 結果
 
  1. 本專題設計了一個診所整合民眾及醫事人員可以共用的整合系統，透過MySQL以及Python實現後端架構，並且依據正規劃原則設計出資料庫架構，其達到第三正規化。
  2. 依據實驗操作之結果，我們可以判斷本資料庫系統在設計及運行上順利，並且可以成為正式系統進行運行。
  3. 指令插入沒有錯誤，增加了系統的可利用性。如此設計，診所本地電腦不用自建系統，預約者以及管理者只需透過雲端即可存取系統。

- 討論
 
  1. 根據文獻說明透過3NF設計，系統可以由不同的TABLE管理，大量減少了Data Redundancy.  其在冗餘控制與結構品質上是合理平衡點 。未來在設計上如果有更大的擴充可以討論4NF及5NF
  2. 3NF在需求改變時，對表格的修改影響範圍較小，更易於維護和管理。

- 限制

  1. 系統現階段沒有使用如SQL Server等企業級資料庫，其提供比較強大之安全性及分析工具...等等，針對小型系統可以接受MySQL的架構，若未來診所需要進行數據分析、保護病患隱私...等等則會有隱憂。如需真正上線需要更強大的UI/UX設計。
  2. 由於系統直接上雲端，因此在網路以及系統安全上需要更多的防範

 ### 參考文獻
  <img width="1113" height="533" alt="image" src="https://github.com/user-attachments/assets/6777b72a-0ad2-423b-9a13-bc471e4a3691" />
