# openUI format standard

The standard look for everything our apps create: web pages, slide decks,
Word documents, PDFs, spreadsheets, emails and other files. It is the openUI
style shared by Prelegal and `pm`. **Use it for every future build unless a
ticket or the user says otherwise.**

The source of truth for the values is `frontend/src/app/globals.css`, which has
the same tokens as `pm/frontend/src/app/globals.css`. If a value changes,
change it there, in `pm`, and in this file together.

openUI's legal name and company details, which every agreement and formal
document uses, are in section 11.

---

## 1. Logo

| | |
|---|---|
| File | `frontend/src/assets/openui-logo.png` (862 × 167 px, transparent PNG, aspect ratio about 5.2 : 1). Favicon: `frontend/src/app/icon.png` |
| Web sizes | **140 px** wide in page headers; **172 px** on a centred hero or sign-in card |
| Documents and slides | 3.5 cm (1.4 in) wide in a Word or PDF header; 4 cm (1.6 in) on a title slide; 2.5 cm (1 in) in a slide footer |
| Minimum width | 96 px on screen, 2.5 cm in print |
| Clear space | At least half the logo's height on every side |
| Background | White (`#ffffff`) or surface (`#f6f8f7`) only |
| Placement | Top left, followed by the product name in the display font (e.g. "Prelegal") |

Never stretch, recolour, outline, rotate or add a shadow to the logo, and never
put it on teal, orange or a photo. On the web, load it through the bundler
(`next/image`) so it works under any base path, and give it `alt="openUI"`.

---

## 2. Colour

### Brand palette

| Token | Hex | Use for | Contrast on white |
|---|---|---|---|
| `--navy-dark` | `#263c3d` | Headings and body text | 11.7 : 1 |
| `--brand-teal-ink` | `#315f62` | Primary buttons (white text), links, eyebrows, key accents | 7.1 : 1 |
| `--brand-teal` | `#4c7f82` | Focus outlines and borders, hover states, large decorative accents | 4.5 : 1 |
| `--brand-orange` | `#d57e39` | **Decoration only**: the active tab underline, accent bars, chart highlights. Never text | 3.1 : 1 (too low for text) |
| `--brand-orange-ink` | `#8f4a1b` | Errors, warnings and destructive actions (text and borders) | 6.6 : 1 |
| `--gray-text` | `#666666` | Secondary text: hints, captions, metadata, footers | 5.7 : 1 |

### Neutrals

| Token | Value | Use for |
|---|---|---|
| `--surface` | `#f6f8f7` | Page background, soft fills, table header rows, assistant chat bubbles |
| `--surface-strong` | `#ffffff` | Panels, cards, document "paper" |
| `--stroke` | `rgba(49, 95, 98, 0.14)`; solid on white: `#e2e9e9` | Borders, dividers, gridlines |
| Table rule | `rgba(49, 95, 98, 0.28)`; solid on white: `#c5d2d3` | Table borders in documents and PDFs |
| `--shadow` | `0 18px 40px rgba(49, 95, 98, 0.12)` | Panels and cards (web only) |

### Rules

- **Text** is navy, secondary text is gray, and links are teal-ink. Body text
  uses no other colours.
- **Orange is never text.** Use orange-ink for errors, and plain orange only for
  shapes and lines.
- **Fills:** white text sits only on teal-ink (7.1 : 1) or navy (11.7 : 1). An
  error panel uses an orange tint (`#d57e39` at 10 %) with orange-ink text.
- **Accessibility:** keep WCAG AA, at least 4.5 : 1 for text and 3 : 1 for large
  text and UI parts. Never use colour alone to show meaning; pair it with
  text or an icon.

### Charts and data

Use the series in this order: teal-ink `#315f62`, orange `#d57e39`, navy
`#263c3d`, orange-ink `#8f4a1b`, gray `#666666`. Set gridlines and axes in
`#e2e9e9` and labels in gray. Keep to four series or fewer per chart where you
can, and label the series directly instead of relying on a legend.

---

## 3. Typography

| Role | Font | Weight | Fallbacks |
|---|---|---|---|
| Display: headings, product name, slide titles | **Space Grotesk** | 600 (semibold) | Segoe UI, Arial, sans-serif |
| Body: text, UI, tables | **Manrope** | 400; 500–600 for labels and emphasis | Segoe UI, Calibri, Arial, sans-serif |
| Legal agreement text (preview) | Georgia | 400 / 700 | "Times New Roman", serif |
| Legal agreement text (PDF) | Noto Sans (bundled, covers Latin, Greek and Cyrillic) | 400 / 700 | none (embedded) |

On the web, self-host the fonts (Fontsource packages `@fontsource-variable/manrope`
and `@fontsource-variable/space-grotesk`) and never load them from Google
Fonts at build time. In Office files, use the fonts if they are installed or
embedded; otherwise use the fallbacks in the table.

### Web type scale

| Element | Size / line height | Style |
|---|---|---|
| Hero heading (sign-in card) | 30 px | Display, semibold, navy |
| Page heading (h1) | 24 px | Display, semibold, navy (`HEADING`) |
| Section heading (h2) | 20 px | Display, semibold, navy (`SUBHEADING`) |
| Eyebrow (above a heading) | 12 px, letter spacing 0.25 em (0.3 em on a hero) | Body, semibold, UPPERCASE, teal-ink |
| Body | 14–16 px / 1.5–1.6 | Body, navy |
| Labels and buttons | 14 px | Body, semibold |
| Hints, captions, footer | 12 px | Body, gray |

---

## 4. Web pages

### Layout

- **Content width:** at most **1500 px**, centred, with **24 px** side gutters
  at every width. Header, content and footer share the same edges.
- **Page background:** `--surface`. Content sits in white panels.
- **Header:** white at 90 % with a bottom stroke. The logo (140 px) and product
  name are on the left; the account and a secondary "Sign out" button are on
  the right. Section tabs sit below, and the active tab has a 2 px orange
  underline and navy text.
- **Footer:** gray 12 px text with a top stroke. It carries the draft or legal
  disclaimer where one applies.
- **Spacing:** use a 4 px grid. Typical gaps are 12, 16 and 24 px; 24 px is the
  panel padding.

### Components (`frontend/src/components/ui.tsx`)

| Component | Spec |
|---|---|
| Panel / card | White, 24 px radius (`rounded-3xl`), 1 px stroke border, `--shadow`, 24 px padding |
| Primary button | Pill (fully rounded), teal-ink fill, white semibold 14 px text, hover `brightness(1.1)` |
| Secondary button | Pill, white, stroke border, teal-ink text; border turns teal on hover |
| Ghost button | Pill, no border, teal-ink text, surface fill on hover |
| Danger button | Pill, white, stroke border, orange-ink text; border turns orange on hover |
| Button sizes | sm 12×6 px padding, md 16×8 px, lg 20×12 px |
| Text input | 12 px radius (`rounded-xl`), stroke border, white, 14 px navy text, gray placeholder; border turns teal on focus and orange-ink when invalid. Label above in 14 px semibold navy; hint below in 12 px gray; error below in 14 px orange-ink |
| Focus | 2 px teal outline, offset 2 px, on every interactive element |
| Chat bubbles | 16 px radius. The user's bubble is teal-ink with white text; the assistant's is surface with navy text |
| Alerts | 16 px radius, orange tint fill, orange-ink text, `role="alert"` |
| Disabled | 50 % opacity and a not-allowed cursor |

### Checklist for a new page

1. Use the tokens and the `ui.tsx` components; don't use raw hex values or a
   new palette.
2. Use the display font for headings and Manrope for everything else.
3. Give the page a two-to-four word `<title>`, such as "My documents | Prelegal".
4. Make sure it works at phone width (no horizontal scroll), is keyboard
   accessible with visible focus, and meets AA contrast.

---

## 5. Slide decks (PowerPoint, Google Slides, PDF slides)

- **Size:** 16:9 (13.33 × 7.5 in, or 1920 × 1080 px).
- **Backgrounds:** white for content slides and `#f6f8f7` for title and section
  slides. No photos behind text, and no gradients.
- **Title slide:**
  - The logo at 4 cm, top left.
  - An eyebrow line: Manrope, 12–14 pt, uppercase, letter spacing 0.25 em, teal-ink.
  - The title: Space Grotesk, 40–44 pt, semibold, navy.
  - The subtitle: Manrope, 18–20 pt, gray.
  - A 4 pt orange accent bar, 1.5 in long, under the title.
- **Section slides:** surface background, the section title at 36 pt in Space
  Grotesk, and the orange accent bar.
- **Content slides:**
  - The title: Space Grotesk, 28–32 pt, semibold, navy, top left, with a
    0.5 in margin.
  - Body: Manrope, 16–20 pt, navy, with at most six bullets and no
    sentence-long bullets.
  - Callouts: white cards with a 0.25 in corner radius and a `#e2e9e9` border.
    Put one key number per card in teal-ink.
- **Footer:**
  - The logo at 2.5 cm, bottom left.
  - The slide number, bottom right, in gray 10 pt.
  - "Draft" or "Confidential" in gray if needed.
- **Charts and tables:** use the chart palette in section 2. In tables, the
  header row has a surface fill and bold navy text, and rules are `#e2e9e9`.

---

## 6. Word documents

- **Page:** A4 (or US Letter for US readers), with 2.54 cm (1 in) margins.
- **Header:** the logo at 3.5 cm on the left. The document title can go on the
  right in 9 pt gray.
- **Footer:** "Page X of Y" in 9 pt gray on the right. A draft or confidentiality
  notice goes on the left in 8–9 pt gray where needed.
- **Styles** (define them as Word styles; don't format headings by hand):

| Style | Font, size | Colour, spacing |
|---|---|---|
| Title | Space Grotesk 26 pt semibold | Navy; 6 pt after; an eyebrow line above in 10 pt uppercase teal-ink |
| Heading 1 | Space Grotesk 18 pt semibold | Navy; 18 pt before, 6 pt after |
| Heading 2 | Space Grotesk 14 pt semibold | Teal-ink; 12 pt before, 4 pt after |
| Heading 3 | Manrope 11 pt bold | Navy; 10 pt before, 2 pt after |
| Body | Manrope 11 pt | Navy; line spacing 1.25; 6 pt after |
| Caption, notes | Manrope 9 pt | Gray |
| Hyperlink | Body | Teal-ink, underlined |

- **Tables:**
  - The header row has a `#f6f8f7` fill and bold navy text, and repeats on each page.
  - Borders are 0.5 pt `#c5d2d3`.
  - Cells have 4 pt padding.
- **Lists:** use round bullets in teal-ink and the "1." style for numbered lists.
- **Callouts:** a box with a `#f6f8f7` fill and a 3 pt teal-ink left border.
  Warnings use an orange-ink left border.

---

## 7. PDFs

- **Reports and other generated documents** follow the Word rules in section 6:
  logo header, styles, table rules and page-numbered footer. Embed the fonts,
  and set the PDF title and author metadata.
- **Legal agreements** (Prelegal's output) keep their plain "paper" look, so they
  read like standard contracts. In `frontend/src/nda/NdaPdf.tsx`:
  - Noto Sans 10 pt in navy, headings in bold at the same font.
  - Table rules `#c5d2d3`, header fills `#f6f8f7`, links teal-ink.
  - A centred gray 8 pt footer that includes "Draft – subject to legal review
    before signing", or "Signed electronically on <date>" once an agreement
    (such as the onboarding NDA with openUI) has been signed.
  - No logo on the agreement itself.
- **Names:** use descriptive file names, such as
  `Mutual-NDA-Acme-Globex.pdf` (see `pdfFilename`).

---

## 8. Spreadsheets

- **Header row:** teal-ink fill, white bold Manrope (or Calibri) text, frozen.
- **Banded rows:** optionally alternate white and `#f6f8f7`.
- **Gridlines:** `#e2e9e9`.
- **Numbers:** right-aligned with consistent decimals. Negative values in
  orange-ink, never red.
- **Charts:** use the palette in section 2.
- **Title area:** the sheet title in row 1 in Space Grotesk 16 pt navy, with a
  short gray note under it giving the source and the date.

---

## 9. Emails and other files

- **Emails:** no logo images inside the body unless the email is a newsletter.
  Use navy text and teal-ink links. The signature is the product name in
  semibold and one gray line.
- **Diagrams:**
  - Boxes are white with `#c5d2d3` borders and an 8–12 px radius.
  - Arrows and connectors are teal-ink, with one orange highlight at most.
  - Labels are Manrope, navy.
- **Icons:** single-colour line icons, in navy or teal-ink.

---

## 10. Where it lives in Prelegal

| What | File |
|---|---|
| Tokens and Tailwind utilities | `frontend/src/app/globals.css` |
| Components | `frontend/src/components/ui.tsx`, `SiteHeader.tsx`, `SiteFooter.tsx`, `Logo.tsx` |
| Fonts | `frontend/src/app/layout.tsx` (Fontsource imports) |
| Logo and favicon | `frontend/src/assets/openui-logo.png`, `frontend/src/app/icon.png` |
| Document preview and PDF | `frontend/src/nda/nda.css` (`--nda-*` variables default to this palette), `frontend/src/nda/NdaPdf.tsx` |
| openUI's legal details (section 11) | `provider.json` (read by the backend and the frontend) |
| openUI's Terms and Conditions | `templates/openui-terms.md` |

---

## 11. openUI's legal details

openUI is the main party to every agreement Prelegal drafts, and the party
named in its Terms and Conditions. Use these details, word for word, wherever
an agreement, letter, invoice or other formal document identifies openUI:

> **Open Universal Inclusion Ltd**, a company incorporated in the British Virgin
> Islands under registration number 1047345, with registered office at Vistra
> Corporate Services Center, Wickhams Cay II, Road Town, Tortola, VG 1110,
> British Virgin Islands ("**openUI**" or the "**Consultant**").

| Detail | Value |
|---|---|
| Legal name | Open Universal Inclusion Ltd |
| Short name | openUI (always this spelling: lower-case "open", upper-case "UI") |
| Defined term | "openUI" or the "Consultant"; the other party is the "Client" (or the "Member" if openUI operates as an association) |
| Entity | Company incorporated in the British Virgin Islands, registration number 1047345 |
| Registered office and notice address | Vistra Corporate Services Center, Wickhams Cay II, Road Town, Tortola, VG 1110, British Virgin Islands |
| Default governing law and courts | The British Virgin Islands (a starting point; agreements other than the onboarding NDA can change it) |

In Prelegal:

- `provider.json` holds these details. The backend fills openUI in as the
  Provider (the Company in a Partnership Agreement, party 1 in the Mutual NDA)
  of every agreement and puts the details back on every save, so they can't be
  edited. The forms show openUI's fields as read-only.
- Each agreement's cover page identifies openUI with the sentence above.
- `type` in `provider.json` is `company` or `association`. It switches the
  Terms' wording (Client or Member, fees or membership subscription).
- The signer shown for openUI (`signerName`, `signerTitle`) is a placeholder
  ("Authorised Signatory", "Director") until openUI names a real signatory.
- Changing the Terms' wording? Bump the `version` line in
  `templates/openui-terms.md`: every user is asked to accept the new version.
