

To create new variables in the gcloud secrets manager
gcloud secrets create META_PHONE_NUMBER_ID --replication-policy=automatic

gcloud secrets create WHATSAPP_BUSSINESS_ID --replication-policy=automatic

echo -n "919339574596127" | gcloud secrets versions add META_PHONE_NUMBER_ID --data-file=-


echo | set /p="help_u_secure_verify_2026" > verify_token.txt
gcloud secrets versions add WHATSAPP_VERIFY_TOKEN --data-file=verify_token.txt
del verify_token.txt


echo | set /p="EAAT3RrysZBD8BRAWhfyx7Ls1SheYKNipF0UPw4YdgGXXKa2zFBLCvbaCB9ILsv8ZCAMcFy9oJ2L79sa5FAWtQHmIma6DmkeQMuAa4HVspGS8J2qnXDuZCiMRrsDagTbAjAXOC4oasdIuva1FZCxZBuPKYKtlNqLXh2tGgkpuyRiwp60cXBS6y9u2cQFBETaWqbQZDZD" > meta_token.txt
gcloud secrets versions add META_ACCESS_TOKEN --data-file=meta_token.txt
del meta_token.txt


alternate way for powershell
$token = 'EAAT3RrysZBD8BRAWhfyx7Ls1SheYKNipF0UPw4YdgGXXKa2zFBLCvbaCB9ILsv8ZCAMcFy9oJ2L79sa5FAWtQHmIma6DmkeQMuAa4HVspGS8J2qnXDuZCiMRrsDagTbAjAXOC4oasdIuva1FZCxZBuPKYKtlNqLXh2tGgkpuyRiwp60cXBS6y9u2cQFBETaWqbQZDZD'
$token.Length
[System.IO.File]::WriteAllText((Join-Path $PWD "meta_token.txt"), $token)
(Get-Item .\meta_token.txt).Length
gcloud secrets versions add META_ACCESS_TOKEN --data-file=.\meta_token.txt
Remove-Item .\meta_token.txt

$token = '919339574596127'
$token.Length
[System.IO.File]::WriteAllText((Join-Path $PWD "meta_phone_number_id.txt"), $token)
(Get-Item .\meta_phone_number_id.txt).Length
gcloud secrets versions add META_PHONE_NUMBER_ID --data-file=.\meta_phone_number_id.txt
Remove-Item .\meta_phone_number_id.txt


### WHATSAPP_BUSSINESS_ID

$waba_id = '1260970375838803'
$waba_id.Length
[System.IO.File]::WriteAllText((Join-Path $PWD "waba_id.txt"), $waba_id)
(Get-Item .\waba_id.txt).Length
gcloud secrets versions add WHATSAPP_BUSSINESS_ID --data-file=.\waba_id.txt
Remove-Item .\waba_id.txt


#### testing api

curl -X GET "https://graph.facebook.com/v24.0/919339574596127?fields=verified_name,display_phone_number,quality_rating,name_status,whatsapp_business_account" ^
  -H "Authorization: Bearer YOUR_META_ACCESS_TOKEN"