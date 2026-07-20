# Design: Multiplayer Sound & Player Color Indicator

## Bug Analysis

### Bug 1 – No Sound
**Root cause**: `run_client.py` אינו קורא ל-`init_sounds()` ואין לו EventBus. אירועי `"sound"` מגיעים מהשרת ב-`poll_events()` אבל לעולם לא מעובדים.

**Fix**: בלולאה הראשית של `run_client.py`, לאחר `bridge.poll_events()`, לעבד כל אירוע sound ולקרוא ל-`_play(name)` מ-`sound_player.py`.

```python
for event in bridge.poll_events():
    if event.get("type") == "sound":
        from kungfu_chess.view.sound_player import _play
        _play(event.get("name", "") + ".mp3")
```

**אלטרנטיבה שנדחתה**: יצירת EventBus ב-`run_client.py` — מסורבל ומיותר כי אירועי Sound כבר מגיעים כ-dict מהשרת.

---

### Bug 2 – No Player Color Indicator
**Root cause**: `view.render()` לא מקבל פרמטר `local_color`. `panel_renderer.py` מציג "Black"/"White" אבל לא מסמן מי מהם הוא "אתה".

**Fix in two parts**:

#### Part A – `image_view.py`
הוסף פרמטר `local_color: str = None` ל-`render()`. העבר אותו ל-`_draw_panels()`, שם יוסיף מסגרת צבעונית על הפאנל של השחקן המקומי.

#### Part B – `panel_renderer.py`
הוסף פרמטר `is_local: bool = False` ל-`draw()`. כאשר `is_local=True`, הוסף:
1. מסגרת צהובה/זהב עבה על הפאנל (`cv2.rectangle`)
2. תווית `"▶ YOU"` מתחת לשם השחקן

#### Part C – `run_client.py`
העבר `local_color=bridge.color().name` לקריאת `view.render(...)`.

## Component Changes

| קובץ | שינוי |
|------|-------|
| `client/run_client.py` | 1. עיבוד אירועי sound מ-`poll_events()` <br> 2. העברת `local_color` ל-`view.render()` |
| `kungfu_chess/view/image_view.py` | הוספת `local_color` ל-`render()` ו-`_draw_panels()` |
| `kungfu_chess/view/panel_renderer.py` | הוספת `is_local` ל-`draw()` עם מסגרת + תווית "▶ YOU" |

## Visual Design

```
┌──────────────────────┐
│  ███████ YOU ███████  │  ← מסגרת זהב כפולה + תווית
│  ▶ YOU               │
│  PlayerName          │
│  Score: 5            │
└──────────────────────┘
```

צבע המסגרת: `(0, 215, 255)` (זהב/ציאן) — בולט על רקע כהה וגם בהיר.
עובי מסגרת: 3 פיקסלים.
