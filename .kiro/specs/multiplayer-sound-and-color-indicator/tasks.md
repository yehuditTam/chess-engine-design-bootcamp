# Tasks: Multiplayer Sound & Player Color Indicator

## Task 1: Fix Sound in Multiplayer
**File**: `client/run_client.py`
**Status**: todo

בלולאה הראשית, לאחר `bridge.poll_events()`, הוסף עיבוד אירועי sound:

```python
events = bridge.poll_events()
for event in events:
    if event.get("type") == "sound":
        from kungfu_chess.view import sound_player
        sound_player._play(event.get("name", "") + ".mp3")
```

---

## Task 2: Add `is_local` to PanelRenderer
**File**: `kungfu_chess/view/panel_renderer.py`
**Status**: todo

בפונקציה `draw()`, הוסף פרמטר `is_local: bool = False`.
כאשר `is_local=True`:
1. צייר מסגרת זהב עבה:
   ```python
   if is_local:
       cv2.rectangle(panel, (0, 0), (w - 1, h - 1), (0, 215, 255), 3)
   ```
2. הוסף תווית `"▶ YOU"` מתחת לשם השחקן (ב-`_PLAYER_Y + 18` לדוגמה):
   ```python
   if is_local:
       self._text(panel, "▶ YOU", w // 2, _PLAYER_Y + 18, 0.45, (0, 215, 255), bold=True)
   ```

---

## Task 3: Pass `local_color` Through ImageView
**File**: `kungfu_chess/view/image_view.py`
**Status**: todo

1. הוסף `local_color: str = None` לפרמטרי `render()`
2. העבר ל-`_draw_panels()`: הוסף `local_color=local_color`
3. ב-`_draw_panels()`, חשב `is_local` לכל פאנל:
   ```python
   black_is_local = (local_color is not None and local_color.lower() == "black")
   white_is_local = (local_color is not None and local_color.lower() == "white")
   ```
4. העבר `is_local=black_is_local` לפאנל השחור ו-`is_local=white_is_local` לפאנל הלבן

---

## Task 4: Wire Both Fixes in run_client.py
**File**: `client/run_client.py`
**Status**: todo

בקריאת `view.render(...)`, הוסף:
```python
local_color=bridge.color().name,
```

ודא שייבוא `sound_player` קיים בראש הקובץ או כ-lazy import בתוך הלולאה.

---

## Verification
- [ ] פתח שני חלונות עם `python -m client.run_client`
- [ ] הזז כלי — שניהם שומעים "click"
- [ ] אכול כלי — שניהם שומעים "eat"  
- [ ] וודא שבכל חלון הפאנל של השחקן המקומי מוקף מסגרת זהב עם "▶ YOU"
- [ ] השחקן הלבן רואה מסגרת על הפאנל הלבן בלבד
- [ ] השחקן השחור רואה מסגרת על הפאנל השחור בלבד
