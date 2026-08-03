"""78장 메타데이터, 방향별 TXT, 자체 SVG 플레이스홀더를 생성한다."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAJORS = [
 ("the_fool","바보","The Fool"),("the_magician","마법사","The Magician"),("the_high_priestess","여사제","The High Priestess"),
 ("the_empress","여황제","The Empress"),("the_emperor","황제","The Emperor"),("the_hierophant","교황","The Hierophant"),
 ("the_lovers","연인","The Lovers"),("the_chariot","전차","The Chariot"),("strength","힘","Strength"),("the_hermit","은둔자","The Hermit"),
 ("wheel_of_fortune","운명의 수레바퀴","Wheel of Fortune"),("justice","정의","Justice"),("the_hanged_man","매달린 사람","The Hanged Man"),
 ("death","죽음","Death"),("temperance","절제","Temperance"),("the_devil","악마","The Devil"),("the_tower","탑","The Tower"),
 ("the_star","별","The Star"),("the_moon","달","The Moon"),("the_sun","태양","The Sun"),("judgement","심판","Judgement"),("the_world","세계","The World")]
SUITS = [("wands","완드","Wands"),("cups","컵","Cups"),("swords","소드","Swords"),("pentacles","펜타클","Pentacles")]
RANKS = [("ace","에이스","Ace"),("two","2","Two"),("three","3","Three"),("four","4","Four"),("five","5","Five"),("six","6","Six"),("seven","7","Seven"),("eight","8","Eight"),("nine","9","Nine"),("ten","10","Ten"),("page","페이지","Page"),("knight","나이트","Knight"),("queen","퀸","Queen"),("king","킹","King")]

def cards():
    result=[]
    for i,(slug,ko,en) in enumerate(MAJORS):
        result.append((f"{i:02}_{slug}",ko,en,"major"))
    index=22
    for suit,suit_ko,suit_en in SUITS:
        for rank,rank_ko,rank_en in RANKS:
            result.append((f"{index:02}_{rank}_of_{suit}",f"{suit_ko} {rank_ko}",f"{rank_en} of {suit_en}",suit)); index+=1
    return result

UP = ["가능성", "전진", "명료함"]
REV = ["재점검", "지연", "내면의 과제"]

def main():
    metadata=[]
    for card_id,ko,en,arcana in cards():
        metadata.append({"id":card_id,"name_ko":ko,"name_en":en,"arcana":arcana,"image_url":f"/static/images/tarot/{card_id}.svg",
                         "keywords":{"upright":UP,"reversed":REV}})
        directory=ROOT/"knowledge"/"tarot"/card_id; directory.mkdir(parents=True,exist_ok=True)
        for orientation,keywords,tone in [("upright",UP,"에너지가 비교적 자연스럽게 표현되는 흐름"),("reversed",REV,"에너지가 막히거나 내면에서 재검토되는 흐름")]:
            content=f"""[CARD_ID]\n{card_id}\n\n[CARD_NAME_KO]\n{ko}\n\n[CARD_NAME_EN]\n{en}\n\n[ORIENTATION]\n{orientation}\n\n[CORE_KEYWORDS]\n{', '.join(keywords)}\n\n[CORE_MEANING]\n{ko} 카드는 {tone}을 상징한다. 질문과 스프레드 자리의 맥락에서 해석한다.\n\n[CURRENT_SITUATION]\n현재 확인 가능한 사실과 감정의 차이를 살필 필요가 있다.\n\n[PSYCHOLOGY]\n익숙한 반응과 실제 바람을 구분하여 바라본다.\n\n[LOVE]\n상대의 의도를 단정하지 말고 대화와 행동을 통해 확인한다.\n\n[CAREER]\n기회와 비용, 준비 수준을 함께 비교한다.\n\n[MONEY]\n구체적인 수치와 감당 가능한 위험 범위를 먼저 확인한다.\n\n[ACTION]\n작게 검증할 수 있는 다음 행동을 선택한다.\n\n[WARNING]\n카드 한 장만으로 실제 사건을 확정하지 않는다.\n"""
            (directory/f"{orientation}.txt").write_text(content,encoding="utf-8")
        svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="500" viewBox="0 0 300 500"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#20133d"/><stop offset="1" stop-color="#6d3f86"/></linearGradient></defs><rect width="300" height="500" rx="18" fill="url(#g)"/><rect x="13" y="13" width="274" height="474" rx="13" fill="none" stroke="#d9ba73" stroke-width="3"/><circle cx="150" cy="205" r="73" fill="none" stroke="#d9ba73" stroke-width="2"/><path d="M150 115l13 64 62 26-62 26-13 64-13-64-62-26 62-26z" fill="#d9ba73" opacity=".85"/><text x="150" y="385" text-anchor="middle" fill="#fff8e8" font-family="sans-serif" font-size="21">{en}</text><text x="150" y="423" text-anchor="middle" fill="#d9ba73" font-family="sans-serif" font-size="18">{ko}</text></svg>'''
        image=ROOT/"app"/"static"/"images"/"tarot"/f"{card_id}.svg"; image.parent.mkdir(parents=True,exist_ok=True); image.write_text(svg,encoding="utf-8")
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"tarot_cards.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"generated {len(metadata)} cards and {len(metadata)*2} knowledge files")

if __name__ == "__main__": main()

