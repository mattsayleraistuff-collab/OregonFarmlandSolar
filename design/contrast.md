# Contrast and colour-blind checks

Every pairing the screens use, computed with the WCAG 2.2 formula. Text needs 4.5:1 (3:1 for 24px and larger). Graphics, control edges and focus rings need 3:1. Figures are light / dark.

## Text pairings (need 4.5:1)

| Foreground | Background | Light | Dark | Used for |
|---|---|---|---|---|
| `ink` #1D1F21 / #ECEFF2 | `bg` #F7F6F2 / #101418 | 15.3:1 pass | 16.0:1 pass | Body text on page |
| `ink` #1D1F21 / #ECEFF2 | `surface` #FFFFFF / #181E24 | 16.5:1 pass | 14.6:1 pass | Body text on cards, tables |
| `ink` #1D1F21 / #ECEFF2 | `sunken` #ECEAE3 / #0B0E11 | 13.7:1 pass | 16.8:1 pass | Text on table headers, empty states |
| `ink-muted` #4A4F55 / #AEB7C0 | `bg` #F7F6F2 / #101418 | 7.6:1 pass | 9.1:1 pass | Captions on page |
| `ink-muted` #4A4F55 / #AEB7C0 | `surface` #FFFFFF / #181E24 | 8.3:1 pass | 8.3:1 pass | Captions on cards |
| `ink-muted` #4A4F55 / #AEB7C0 | `sunken` #ECEAE3 / #0B0E11 | 6.9:1 pass | 9.5:1 pass | Captions on recessed areas |
| `accent` #0B4F8A / #8EC1F5 | `bg` #F7F6F2 / #101418 | 7.8:1 pass | 9.8:1 pass | Links on page |
| `accent` #0B4F8A / #8EC1F5 | `surface` #FFFFFF / #181E24 | 8.4:1 pass | 8.9:1 pass | Links on cards |
| `accent` #0B4F8A / #8EC1F5 | `sunken` #ECEAE3 / #0B0E11 | 7.0:1 pass | 10.2:1 pass | Links in footer, empty states |
| `on-accent` #FFFFFF / #0B1B2B | `accent` #0B4F8A / #8EC1F5 | 8.4:1 pass | 9.2:1 pass | Primary button, selected switch option |
| `bg` #F7F6F2 / #101418 | `ink` #1D1F21 / #ECEFF2 | 15.3:1 pass | 16.0:1 pass | Step numbers on timeline |
| `ink` #1D1F21 / #ECEFF2 | `info-bg` #E3EEF9 / #12263A | 14.1:1 pass | 13.3:1 pass | Scope notice |
| `ink` #1D1F21 / #ECEFF2 | `caution-bg` #FFF1D6 / #2B2110 | 14.8:1 pass | 13.7:1 pass | “Not pooled, not final” notice |
| `synth-ink` #1A1400 / #1A1400 | `synth-bg` #FFD23F / #FFD23F | 12.7:1 pass | 12.7:1 pass | Synthetic data banner and tags |
| `approve-ink` #0A3F6E / #D3E6F9 | `approve-bg` #E1EEF9 / #16314A | 9.1:1 pass | 10.5:1 pass | “Approved” chip |
| `deny-ink` #6E2900 / #FBD7BF | `deny-bg` #FBE6D8 / #3A2112 | 8.8:1 pass | 11.1:1 pass | “Denied” chip |
| `seq-1-ink` #1D1F21 / #FFFFFF | `seq-1` #C6DBEF / #1F4A73 | 11.6:1 pass | 9.2:1 pass | Map count label, class 1 |
| `seq-2-ink` #1D1F21 / #FFFFFF | `seq-2` #9ECAE1 / #2F6EA6 | 9.4:1 pass | 5.4:1 pass | Map count label, class 2 |
| `seq-3-ink` #1D1F21 / #0B0E11 | `seq-3` #6BAED6 / #5B97CB | 6.8:1 pass | 6.2:1 pass | Map count label, class 3 |
| `seq-4-ink` #FFFFFF / #0B0E11 | `seq-4` #2171B5 / #93C0E8 | 5.1:1 pass | 10.1:1 pass | Map count label, class 4 |
| `seq-5-ink` #FFFFFF / #0B0E11 | `seq-5` #08306B / #D3E7F8 | 12.8:1 pass | 15.3:1 pass | Map count label, class 5 |

## Graphics, edges and focus (need 3:1)

| Foreground | Background | Light | Dark | Used for |
|---|---|---|---|---|
| `border-strong` #6F6B60 / #8794A2 | `bg` #F7F6F2 / #101418 | 4.9:1 pass | 6.0:1 pass | Input, button and chip edges |
| `border-strong` #6F6B60 / #8794A2 | `surface` #FFFFFF / #181E24 | 5.3:1 pass | 5.4:1 pass | Input edges on cards |
| `border-strong` #6F6B60 / #8794A2 | `sunken` #ECEAE3 / #0B0E11 | 4.4:1 pass | 6.3:1 pass | Chip edges on recessed areas |
| `focus` #B34700 / #FFC24D | `bg` #F7F6F2 / #101418 | 5.1:1 pass | 11.5:1 pass | Focus ring on page |
| `focus` #B34700 / #FFC24D | `surface` #FFFFFF / #181E24 | 5.5:1 pass | 10.5:1 pass | Focus ring on cards |
| `focus` #B34700 / #FFC24D | `sunken` #ECEAE3 / #0B0E11 | 4.6:1 pass | 12.0:1 pass | Focus ring on recessed areas |
| `map-stroke` #6F6B60 / #8794A2 | `bg` #F7F6F2 / #101418 | 4.9:1 pass | 6.0:1 pass | County outlines on page |
| `map-stroke` #6F6B60 / #8794A2 | `surface` #FFFFFF / #181E24 | 5.3:1 pass | 5.4:1 pass | County outlines on map card |
| `ink` #1D1F21 / #ECEFF2 | `surface` #FFFFFF / #181E24 | 16.5:1 pass | 14.6:1 pass | Chart mark outlines (cat-outline) on cards |
| `ink` #1D1F21 / #ECEFF2 | `bg` #F7F6F2 / #101418 | 15.3:1 pass | 16.0:1 pass | Selected-county outline |
| `info-border` #0B4F8A / #8EC1F5 | `bg` #F7F6F2 / #101418 | 7.8:1 pass | 9.8:1 pass | Scope notice border and icon |
| `caution-border` #8A5300 / #E0A030 | `bg` #F7F6F2 / #101418 | 5.9:1 pass | 8.1:1 pass | Caution notice border and icon |
| `approve-border` #0B4F8A / #7DB7F0 | `approve-bg` #E1EEF9 / #16314A | 7.1:1 pass | 6.3:1 pass | “Approved” chip border on its fill |
| `approve-border` #0B4F8A / #7DB7F0 | `bg` #F7F6F2 / #101418 | 7.8:1 pass | 8.7:1 pass | “Approved” chip border on page |
| `deny-border` #B34700 / #F09A5A | `deny-bg` #FBE6D8 / #3A2112 | 4.6:1 pass | 6.7:1 pass | “Denied” chip border on its fill |
| `deny-border` #B34700 / #F09A5A | `bg` #F7F6F2 / #101418 | 5.1:1 pass | 8.3:1 pass | “Denied” chip border on page |
| `synth-ink` #1A1400 / #1A1400 | `synth-bg` #FFD23F / #FFD23F | 12.7:1 pass | 12.7:1 pass | Synthetic banner stripes and icon |

## Pairings that are deliberately under 3:1, and why that is allowed

- **Category fills against the card**: `cat-4` orange (2.2:1), `cat-5` sky (2.3:1) and `cat-7` yellow (1.3:1) on light; `cat-8` grey (1.9:1) on dark. Every category mark is drawn with a 1.5px `cat-outline` (`ink`) edge, which is 16:1 against the card, and each category also has its own glyph shape, its name in text and its count in text.
- **Neighbouring sequential classes against each other** (1.2:1 to 2.5:1 light, 1.5:1 to 1.7:1 dark). They are ordered by lightness, which is the point of a sequential ramp, and every county with a case carries its number. The table gives the same counts. Each county outline is 4.9:1 (light) and 6:1 (dark) against the page, so no shape depends on its fill to be seen.
- **`border`** (1.5:1 and 1.8:1) is used only for decorative dividers. Anything that marks the edge of a control uses `border-strong`.

## Colour-blind separation

Minimum pairwise distance (CIE Lab ΔE, Machado 2009 simulation, severity 1.0). Higher is easier to tell apart; about 10 or more is clearly distinct.

| Palette | Normal | Protan | Deutan | Tritan |
|---|---|---|---|---|
| Categories (8) | 26.4 | 20.7 | 17 | 16.1 |
| Sequential, light (5) | 10.5 | 7.3 | 9.3 | 13.3 |
| Sequential, dark (5) | 16.2 | 15.7 | 16 | 15.7 |

The weakest sequential pair is class 1 against class 2 in the light theme under protanopia (ΔE 7.3). That is the pair a reader is least likely to need to tell apart, since both are labelled with their counts.
