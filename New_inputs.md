
1. In google sheets, the change request is to have 2 sepeareate sheets for Sales and purchases. All the sales will go into sales sheeet and all the purchases to purchase sheet.
CR - New Expense sheet. User can input text or voice note. this is for the end user
2. Ask Whether Sale / Purchase before recording data through text or voice. This is a 1st setp from the current process we have
3. GSTIN with State of Supply. Double check if the state numbers are assigned properly in the F-column (place of suply). this is has to be preceise. in state - CSGT & SGST are applied else IGST is applied
4. We should explore if we can convert photo of a document into pdf in general where we can give convert to PDF option in general. user takes a photo and uploads from whatsapp. This image should be converted to pdf and stored in gdrive
5. In sale invoice, if the user doen't input GSTIN is not provided, then user should be prompted to input GSTIN. Note: some business will not have GSTIN. Mark it as N/A. But the user has to confirm this.


I tested : found following issues 
1) GSTIN not identifying sender in Purchase, Sale - if the Receipient GSTIN is not provided, we need to ask the user to input or confirm 
2) Single product only taken in recording (user should have option to input more than one product into a sale invoice - both whastapp + FD)
3) not taking any other text other than coded text - how does the use should start inputing sale invoice text or voicce note so that the  system understands. We don't want to stick to have a strcit template. It has to be user agnostic
4) LETS ADDRESS THIS AS LAST ITEM in this list - Critical - Scanning mistakes of Customer or Supplier name , GSTIN , Invoice no. (how to improve this - There are errors while parsing the scanned document - ex: SV Exports is parsed as V Exports, and sometime 9 is treaed as 8 etc) Lets explore if we can use a better openai model for parising invoices. 
5) GSTR1 report of day only coming , only few items. These JSON should be thoroughly analysed for what we require - Take a recheck to see if the data is for entire month from whatsapp. 
6) Let’s create Expenses worksheet like Sales , Purchases where they can take photo of expense bill which can be auto entered into drive
7) Payments worksheet which can be single payment (one time) / Recurring ( monthly / yearly ), which can be auto entered into pruchase worksheet with text / speech
8) In Sales / Purchases , it should ask for B2B or B2C before recording so that GSTIN of B2B is recorded properly. Sale / Purchase ; B2B / B2C
Select in single selection message
9) In Stats - lets get all the possible value additions for the users - like Unpaid Sales ; Unpaid Purchases also like Total Purchases , Total Sales , Sales Invoices , Purchase Invoices