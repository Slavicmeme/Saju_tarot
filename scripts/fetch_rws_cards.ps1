$ErrorActionPreference='Stop'
$root=if($PSScriptRoot){Split-Path -Parent $PSScriptRoot}else{(Get-Location).Path}
$dataPath=Join-Path $root 'data/tarot_cards.json'
$cards=Get-Content -Raw -Encoding UTF8 $dataPath|ConvertFrom-Json
$majorNames=@('Fool','Magician','High Priestess','Empress','Emperor','Hierophant','Lovers','Chariot','Strength','Hermit','Wheel of Fortune','Justice','Hanged Man','Death','Temperance','Devil','Tower','Star','Moon','Sun','Judgement','World')
$suitFiles=@{wands='Wands';cups='Cups';swords='Swords';pentacles='Pents'}
$imageDir=Join-Path $root 'app/static/images/rws';New-Item -ItemType Directory -Force $imageDir|Out-Null
for($i=0;$i -lt $cards.Count;$i++){
  $card=$cards[$i]
  if($i -lt 22){$file=('RWS Tarot {0:D2} {1}.jpg' -f $i,$majorNames[$i])}
  else{$within=($i-22)%14+1;$suit=$card.arcana;$file=('{0}{1:D2}.jpg' -f $suitFiles[$suit],$within)}
  $destination=Join-Path $imageDir "$($card.id).jpg"
  if(!(Test-Path $destination)){
    $encoded=[uri]::EscapeDataString($file)
    $uri="https://commons.wikimedia.org/wiki/Special:Redirect/file/${encoded}?width=480"
    $downloaded=$false
    for($attempt=1;$attempt -le 4 -and !$downloaded;$attempt++){
      try{Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $destination -TimeoutSec 30 -Headers @{'User-Agent'='MagicTarotMVP/0.2 (educational project)'};$downloaded=$true}
      catch{if($attempt -eq 4){throw};Start-Sleep -Seconds (4*$attempt)}
    }
    Start-Sleep -Milliseconds 900
  }
  $card|Add-Member -NotePropertyName fallback_image_url -NotePropertyValue $card.image_url -Force
  $card.image_url="/static/images/rws/$($card.id).jpg"
}
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($dataPath,($cards|ConvertTo-Json -Depth 6),$utf8)
Write-Output "RWS images ready: $(@(Get-ChildItem $imageDir -Filter *.jpg).Count)"
