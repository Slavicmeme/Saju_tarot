$ErrorActionPreference = 'Stop'
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$majorRaw = @'
the_fool|바보|The Fool
the_magician|마법사|The Magician
the_high_priestess|여사제|The High Priestess
the_empress|여황제|The Empress
the_emperor|황제|The Emperor
the_hierophant|교황|The Hierophant
the_lovers|연인|The Lovers
the_chariot|전차|The Chariot
strength|힘|Strength
the_hermit|은둔자|The Hermit
wheel_of_fortune|운명의 수레바퀴|Wheel of Fortune
justice|정의|Justice
the_hanged_man|매달린 사람|The Hanged Man
death|죽음|Death
temperance|절제|Temperance
the_devil|악마|The Devil
the_tower|탑|The Tower
the_star|별|The Star
the_moon|달|The Moon
the_sun|태양|The Sun
judgement|심판|Judgement
the_world|세계|The World
'@
$suits = @(@('wands','완드','Wands'),@('cups','컵','Cups'),@('swords','소드','Swords'),@('pentacles','펜타클','Pentacles'))
$ranks = @(@('ace','에이스','Ace'),@('two','2','Two'),@('three','3','Three'),@('four','4','Four'),@('five','5','Five'),@('six','6','Six'),@('seven','7','Seven'),@('eight','8','Eight'),@('nine','9','Nine'),@('ten','10','Ten'),@('page','페이지','Page'),@('knight','나이트','Knight'),@('queen','퀸','Queen'),@('king','킹','King'))
$items = [System.Collections.Generic.List[object]]::new()
$i=0
foreach($line in ($majorRaw.Trim() -split "`n")){ $p=$line.Trim() -split '\|'; $items.Add([pscustomobject]@{id=('{0:D2}_{1}' -f $i,$p[0]);name_ko=$p[1];name_en=$p[2];arcana='major'});$i++ }
foreach($s in $suits){ foreach($r in $ranks){ $items.Add([pscustomobject]@{id=('{0:D2}_{1}_of_{2}' -f $i,$r[0],$s[0]);name_ko="$($s[1]) $($r[1])";name_en="$($r[2]) of $($s[2])";arcana=$s[0]});$i++ } }
$metadata=@()
foreach($card in $items){
  $metadata += [ordered]@{id=$card.id;name_ko=$card.name_ko;name_en=$card.name_en;arcana=$card.arcana;image_url="/static/images/tarot/$($card.id).svg";keywords=[ordered]@{upright=@('가능성','전진','명료함');reversed=@('재점검','지연','내면의 과제')}}
  $dir=Join-Path $root "knowledge/tarot/$($card.id)"; New-Item -ItemType Directory -Force $dir | Out-Null
  foreach($orientation in @('upright','reversed')){
    $keywords = if($orientation -eq 'upright'){'가능성, 전진, 명료함'}else{'재점검, 지연, 내면의 과제'}
    $tone = if($orientation -eq 'upright'){'에너지가 비교적 자연스럽게 표현되는 흐름'}else{'에너지가 막히거나 내면에서 재검토되는 흐름'}
    $content="[CARD_ID]`n$($card.id)`n`n[CARD_NAME_KO]`n$($card.name_ko)`n`n[CARD_NAME_EN]`n$($card.name_en)`n`n[ORIENTATION]`n$orientation`n`n[CORE_KEYWORDS]`n$keywords`n`n[CORE_MEANING]`n$($card.name_ko) 카드는 $tone 을 상징한다. 질문과 스프레드 자리의 맥락에서 해석한다.`n`n[CURRENT_SITUATION]`n현재 확인 가능한 사실과 감정의 차이를 살핀다.`n`n[PSYCHOLOGY]`n익숙한 반응과 실제 바람을 구분한다.`n`n[LOVE]`n상대의 의도를 단정하지 말고 대화와 행동으로 확인한다.`n`n[CAREER]`n기회와 비용, 준비 수준을 함께 비교한다.`n`n[MONEY]`n구체적인 수치와 감당 가능한 위험을 확인한다.`n`n[ACTION]`n작게 검증할 수 있는 다음 행동을 선택한다.`n`n[WARNING]`n카드 한 장만으로 실제 사건을 확정하지 않는다.`n"
    Set-Content -LiteralPath (Join-Path $dir "$orientation.txt") -Value $content -Encoding utf8
  }
  $imageDir=Join-Path $root 'app/static/images/tarot';New-Item -ItemType Directory -Force $imageDir|Out-Null
  $svg="<svg xmlns='http://www.w3.org/2000/svg' width='300' height='500'><rect width='300' height='500' rx='18' fill='#291747'/><rect x='13' y='13' width='274' height='474' rx='13' fill='none' stroke='#d9ba73' stroke-width='3'/><circle cx='150' cy='205' r='73' fill='none' stroke='#d9ba73'/><path d='M150 115l13 64 62 26-62 26-13 64-13-64-62-26 62-26z' fill='#d9ba73'/><text x='150' y='385' text-anchor='middle' fill='#fff8e8' font-family='sans-serif' font-size='19'>$($card.name_en)</text><text x='150' y='423' text-anchor='middle' fill='#d9ba73' font-family='sans-serif' font-size='18'>$($card.name_ko)</text></svg>"
  Set-Content -LiteralPath (Join-Path $imageDir "$($card.id).svg") -Value $svg -Encoding utf8
}
$dataDir=Join-Path $root 'data';New-Item -ItemType Directory -Force $dataDir|Out-Null
$metadata|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $dataDir 'tarot_cards.json') -Encoding utf8
Write-Output "Generated $($items.Count) cards and $($items.Count*2) knowledge files"
