# Requirements: Multiplayer Sound & Player Color Indicator

## Overview
שני בגים קיימים במצב multiplayer (שני חלונות):
1. צלילים לא מושמעים בחיבור multiplayer
2. לא ברור בכל חלון האם השחקן הוא שחור או לבן

## Background
- בגרסת local (`run_view.py`) הצלילים עובדים כי נקרא `init_sounds(bus)`
- בגרסת multiplayer (`client/run_client.py`) לא נקרא `init_sounds` ואין EventBus
- אירועי sound מגיעים מהשרת דרך `poll_events()` אבל לעולם לא מעובדים
- הפאנל מציג "Black" / "White" כתווית קבועה, ללא כל אינדיקציה מי הוא ה-"אתה"

## Requirements

### REQ-1: Sound in Multiplayer
- **REQ-1.1**: כאשר מגיע אירוע `{"type": "sound", "name": "click"}` דרך `poll_events()`, יש לנגן את הצליל המתאים (`click.mp3`)
- **REQ-1.2**: כאשר מגיע אירוע `{"type": "sound", "name": "eat"}`, יש לנגן `eat.mp3`
- **REQ-1.3**: כאשר מגיע אירוע `{"type": "sound", "name": "jump"}`, יש לנגן `jump.mp3`
- **REQ-1.4**: כאשר מגיע אירוע `{"type": "sound", "name": "game_over"}`, יש לנגן `game_over.mp3`
- **REQ-1.5**: שגיאות בהשמעת צליל לא יפילו את הלולאה הראשית

### REQ-2: Player Color Indicator
- **REQ-2.1**: כל חלון multiplayer חייב להציג בצורה בולטת ומידית לאיזה צבע שייך השחקן המקומי (שחור או לבן)
- **REQ-2.2**: האינדיקציה חייבת להיות גלויה בתוך חלון ה-OpenCV (לא רק ב-terminal)
- **REQ-2.3**: הפאנל של השחקן המקומי יסומן בכותרת "▶ YOU" או מסגרת/הדגשה שמבחינה אותו מהיריב
- **REQ-2.4**: הסימון חייב להיות גלוי כל זמן המשחק, לא רק בהתחלה
- **REQ-2.5**: הסימון לא ישנה את הלייאאוט הקיים — רק יוסיף אינדיקציה ויזואלית

## Acceptance Criteria
- AC-1: כששחקן מזיז כלי, שניהם שומעים "click.mp3"
- AC-2: כששחקן אוכל כלי, שניהם שומעים "eat.mp3"  
- AC-3: כשנגמר המשחק, שניהם שומעים "game_over.mp3"
- AC-4: שחקן שחור רואה אינדיקציה ברורה שהוא "שחור" בחלון שלו
- AC-5: שחקן לבן רואה אינדיקציה ברורה שהוא "לבן" בחלון שלו
