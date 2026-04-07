# Typeform API Reference

Extracted from Typeform Developer Documentation (2026-04-06).

---

## 1. Platform Overview

### Base URLs

| Environment | URL |
|---|---|
| Standard | `https://api.typeform.com/` |
| EU Data Center | `https://api.eu.typeform.com` or `https://api.typeform.eu` |

### Authentication

All API requests require a personal access token or OAuth 2.0 token passed via header:

```
Authorization: Bearer <TOKEN>
```

### Rate Limits

Create and Responses APIs: **2 requests per second per account.** Webhooks and Embed have no rate limits.

### Request/Response Format

All APIs use standard HTTP methods (`POST`, `PUT`, `GET`, `DELETE`) and return JSON.

### Parameter Types

- **Path parameters** (required): Part of the endpoint URL, e.g. `{form_id}`
- **Query parameters** (optional): Appended to filter/paginate results

---

## 2. Create API

### 2.1 Create Form

**`POST /forms`**

Creates a new form. Returns `201` with the complete form object.

#### Top-Level Request Body

| Property | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Form title |
| `type` | string | No | `quiz`, `classification`, `score`, `branching`, `classification_branching`, `score_branching` |
| `settings` | object | No | Form configuration |
| `theme` | object | No | Theme reference with `href` |
| `workspace` | object | No | Workspace assignment with `href` |
| `hidden` | array | No | Hidden field variable names |
| `variables` | object | No | `price` (number) and `score` (integer) |
| `welcome_screens` | array | No | Welcome screen definitions |
| `thankyou_screens` | array | No | Thank you screen definitions |
| `fields` | array | Yes | Form field definitions |
| `logic` | array | No | Logic jump definitions |

#### Field Types

All fields require `ref` (string), `title` (string), and `type`:

`short_text`, `long_text`, `email`, `website`, `phone_number`, `number`, `date`, `time`, `dropdown`, `multiple_choice`, `picture_choice`, `ranking`, `rating`, `opinion_scale`, `yes_no`, `legal`, `statement`, `file_upload`, `payment`, `matrix`, `group`, `contact_info`, `multi_format`, `calendly`, `nps`

#### Field Properties

**Choice fields** (`multiple_choice`, `picture_choice`, `ranking`, `dropdown`):

| Property | Type | Notes |
|---|---|---|
| `choices` | array | Objects with `label` (max 255 chars), `ref`, optional `attachment` |
| `allow_multiple_selection` | boolean | |
| `randomize` | boolean | |
| `allow_other_choice` | boolean | |
| `vertical_alignment` | boolean | multiple_choice/ranking only |
| `alphabetical_order` | boolean | dropdown only |
| `supersized` | boolean | picture_choice only |
| `show_labels` | boolean | picture_choice only, default `true` |

**Scale fields** (`opinion_scale`, `rating`):

| Property | Type | Notes |
|---|---|---|
| `steps` | integer | 5–11 |
| `shape` | string | `star`, `cat`, `circle`, `cloud`, `crown`, `dog`, `droplet`, `flag`, `heart`, `lightbulb`, `pencil`, `skull`, `thunder`, `tick`, `trophy`, `user` |
| `labels` | object | `left`, `right`, `center` strings |
| `start_at_one` | boolean | opinion_scale only |

**Date fields:**

| Property | Values | Default |
|---|---|---|
| `structure` | `DDMMYYYY`, `MMDDYYYY`, `YYYYMMDD` | `DDMMYYYY` |
| `separator` | `/`, `-`, `.` | `/` |

**Number fields:** `min_value`, `max_value` (positive integers)

**Payment fields:**

| Property | Type | Notes |
|---|---|---|
| `currency` | string | `AUD`, `BRL`, `CAD`, `CHF`, `DKK`, `EUR`, `GBP`, `MXN`, `NOK`, `SEK`, `USD` (default: `EUR`) |
| `price` | object | `type`: `variable`, `value`: `price` |
| `email_receipts` | boolean | |
| `additional_payment_methods` | array | `applePay`, `googlePay` |

**Text constraints:** `max_length` (integer) for short_text/long_text

**Selection constraints:** `min_selection`, `max_selection` (integers) for choice fields

**Multi-format fields:** `allowed_answer_types` array including `video`, `audio`, `text`

#### Validations Object

| Property | Applicable Types |
|---|---|
| `required` | Most field types |
| `max_length` | short_text, long_text |
| `min_value`, `max_value` | number |
| `min_selection`, `max_selection` | ranking, multiple_choice, picture_choice |

#### Attachments

**Image:**
```json
{
  "type": "image",
  "href": "https://images.typeform.com/images/kbn8tc98AHb",
  "properties": { "description": "Alt text" }
}
```

**Video:**
```json
{
  "type": "video",
  "href": "https://youtube.com/...",
  "scale": 0.6,
  "properties": { "description": "Alt text" }
}
```
Scale options: `0.4`, `0.6`, `0.8`, `1` (default: `0.6`)

#### Layout

Types: `split`, `wallpaper`, `float`, `stack`

- `placement`: `left` or `right` (for split/float)
- `small`: viewport override for small screens
- `large`: viewport override for large screens

#### Scoring

**Boolean correct:**
```json
{
  "type": "boolean_correct",
  "boolean_correct": { "boolean": true, "score": 10 }
}
```

**Choices all correct:**
```json
{
  "type": "choices_all_correct",
  "choices_all_correct": { "choices": ["ref1", "ref2"], "score": 10 }
}
```

#### Logic Jumps

```json
{
  "type": "field|hidden",
  "ref": "field_reference",
  "actions": [
    {
      "action": "jump|add|subtract|multiply|divide|set",
      "condition": {
        "op": "operator",
        "vars": [
          { "type": "field|hidden|variable|constant|choice", "value": "value" }
        ]
      },
      "details": {
        "to": { "type": "field|thankyou|outcome", "value": "reference" },
        "target": { "type": "variable", "value": "variable_name" },
        "value": { "type": "constant|variable|evaluation", "value": "value" }
      }
    }
  ]
}
```

**Operators:**

- Comparison: `equal`, `not_equal`, `lower_than`, `lower_equal_than`, `greater_than`, `greater_equal_than`
- String: `begins_with`, `ends_with`, `contains`, `not_contains`
- State: `is`, `is_not`, `always_on`, `not_on`
- Date: `earlier_than`, `earlier_than_or_on`, `later_than`, `later_than_or_on`

#### Welcome Screens

```json
{
  "ref": "welcome_ref",
  "title": "Welcome Title",
  "properties": {
    "description": "Welcome text",
    "show_button": true,
    "button_text": "Start"
  },
  "layout": {},
  "attachment": {}
}
```

#### Thank You Screens

```json
{
  "ref": "thankyou_ref",
  "title": "Thank You Title",
  "type": "thankyou_screen|url_redirect",
  "properties": {
    "show_button": true,
    "button_text": "Share",
    "button_mode": "reload|default_redirect|redirect",
    "redirect_url": "https://example.com",
    "share_icons": true
  }
}
```

#### Settings Object

| Property | Type | Default | Description |
|---|---|---|---|
| `language` | string | `en` | Language code |
| `is_public` | boolean | `true` | Form visibility |
| `autosave_progress` | boolean | `true` | Client-side progress saving |
| `progress_bar` | string | `proportion` | `percentage` or `proportion` |
| `show_progress_bar` | boolean | `true` | Display progress bar |
| `show_typeform_branding` | boolean | `true` | Display Typeform logo |
| `show_time_to_complete` | boolean | `true` | Show estimated time |
| `show_number_of_submissions` | boolean | — | Show submission count (mutually exclusive with `show_time_to_complete`) |
| `show_cookie_consent` | boolean | — | Display cookie banner |
| `show_question_number` | boolean | `true` | Display question numbers |
| `show_key_hint_on_choices` | boolean | `true` | Show keyboard shortcuts |
| `hide_navigation` | boolean | — | Hide navigation arrows |
| `captcha` | boolean | — | Enable reCAPTCHA |

**Meta object** (within settings):

| Property | Type | Description |
|---|---|---|
| `title` | string | Form name in workspace |
| `allow_indexing` | boolean | SEO indexing |
| `description` | string | SEO description |
| `image.href` | string | Social sharing image URL |
| `redirect_after_submit_url` | string | Redirect URL after submission |
| `google_analytics` | string | GA tracking ID |
| `facebook_pixel` | string | Pixel ID |
| `google_tag_manager` | string | GTM container ID |
| `mode` | string | `knowledge_quiz` |
| `feedback_mode` | string | `knowledge_quiz_inline` |

**Duplicate prevention** (within settings):

| Property | Type | Values |
|---|---|---|
| `type` | string | `cookie`, `cookie_ip` |
| `responses_limit` | integer | Max responses per period |
| `period` | string | `day`, `week`, `month`, `year` |

#### Contact Info Field

Specialized field with predefined subfields: `first_name` (short_text), `last_name` (short_text), `email` (email), `phone_number` (phone_number with `default_country_code`), `company` (short_text)

#### Constraints

- All image URLs must reference existing Typeform images
- Third-party content injection is prohibited
- Images not in account trigger `IMAGE_NOT_FOUND` error
- Choice labels limited to 255 characters
- Opinion scale/rating: 5–11 steps
- Form requires at least one field

---

### 2.2 Retrieve Form

**`GET /forms/{form_id}`**

Returns `200` with the complete form object including all fields, logic, settings, theme, and workspace references.

**Path parameter:** `form_id` (required) — unique form identifier from the form URL

**Response includes:** `id`, `title`, `language`, `fields`, `hidden`, `variables`, `welcome_screens`, `thankyou_screens`, `logic`, `theme`, `workspace`, `_links`, `settings`, `cui_settings`

**CUI Settings Object:**

| Property | Type | Description |
|---|---|---|
| `avatar` | string | Image URL for conversation avatar |
| `is_typing_emulation_disabled` | boolean | Disable typing animation |
| `typing_emulation_speed` | string | `slow`, `medium`, `fast` |

---

### 2.3 Update Form

**`PUT /forms/{form_id}`**

Overwrites the entire form. Returns `200`.

**Critical:** The PUT request must include ALL existing fields you want to retain, including original `id` values. Omitted fields and their collected responses are permanently deleted.

**Path parameter:** `form_id` (required)

**Request body:** Same schema as Create Form. If `theme` is omitted, Typeform applies a new default theme copy.

---

### 2.4 List Forms

**`GET /forms`**

Returns paginated list of forms. Returns `200`.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `search` | string | — | Filter by string match |
| `page` | integer | `1` | Page number |
| `page_size` | number | `10` | Results per page (max 200) |
| `workspace_id` | string | — | Filter by workspace |
| `sort_by` | string | — | `created_at` or `last_updated_at` |
| `order_by` | string | — | `asc` or `desc` |

**Response:**

```json
{
  "total_items": 25,
  "page_count": 2,
  "items": [
    {
      "id": "abc123",
      "title": "Form Title",
      "created_at": "2024-01-01T00:00:00Z",
      "last_updated_at": "2024-01-02T00:00:00Z",
      "theme": { "href": "..." },
      "settings": { "is_public": true },
      "self": { "href": "..." },
      "_links": { "display": "...", "responses": "..." }
    }
  ]
}
```

---

### 2.5 Workspaces

#### List Workspaces

**`GET /workspaces`**

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `search` | string | — | Filter by string match |
| `page` | integer | `1` | Page number |
| `page_size` | number | `10` | Results per page (max 200) |

**Response:**

```json
{
  "total_items": 10,
  "page_count": 1,
  "items": [
    {
      "account_id": "ABCD1234",
      "id": "a1b2c3",
      "name": "My Workspace",
      "shared": false,
      "forms": {
        "count": 12,
        "href": "https://api.typeform.com/workspaces/a1b2c3/forms"
      },
      "self": [{ "href": "https://api.typeform.com/workspaces/a1b2c3" }]
    }
  ]
}
```

---

### 2.6 Themes

#### Create Theme

**`POST /themes`**

Returns `201` with the created theme object.

**Request Body:**

| Property | Type | Default | Description |
|---|---|---|---|
| `name` | string | — | Theme name |
| `font` | string | `Source Sans Pro` | Google Font name (27 options available) |
| `has_transparent_button` | boolean | — | Transparent button styling |
| `rounded_corners` | string | `small` | `none`, `small`, `large` |
| `colors.answer` | string | `#4FB0AE` | Answer text color |
| `colors.background` | string | `#FFFFFF` | Background color |
| `colors.button` | string | `#4FB0AE` | Button color |
| `colors.question` | string | `#3D3D3D` | Question text color |
| `fields.alignment` | string | `left` | `left` or `center` |
| `fields.font_size` | string | `medium` | `small`, `medium`, `large` |
| `screens.alignment` | string | `center` | `left` or `center` |
| `screens.font_size` | string | `small` | `small`, `medium`, `large` |
| `background.brightness` | number | — | -1 to 1 |
| `background.href` | string | — | Background image URL |
| `background.layout` | string | `fullscreen` | `fullscreen`, `repeat`, `no-repeat` |

**Response includes:** all submitted properties plus `id` (string) and `visibility` (`private` or `public`)

---

## 3. Responses API

### 3.1 Retrieve Responses

**`GET /forms/{form_id}/responses`**

Returns form responses. Very recent submissions (~30 min) may not appear; use webhooks for real-time data.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page_size` | integer | `25` | Max responses per request (max 1000) |
| `since` | string | — | ISO 8601 or Unix timestamp — responses after this date |
| `until` | string | — | ISO 8601 or Unix timestamp — responses before this date |
| `after` | string | — | Cursor-based pagination token (exclusive, incompatible with `sort`) |
| `before` | string | — | Cursor-based pagination token (exclusive, incompatible with `sort`) |
| `included_response_ids` | string | — | Comma-separated response IDs to include |
| `excluded_response_ids` | string | — | Comma-separated response IDs to exclude |
| `response_type` | array | `completed` | `started`, `partial`, `completed` (comma-separated) |
| `completed` | boolean | — | **Deprecated.** Use `response_type` |
| `sort` | string | — | `{fieldID},{asc\|desc}` — built-in: `submitted_at`, `staged_at`, `landed_at` |
| `query` | string | — | Search across answers, hidden fields, variables |
| `fields` | array | — | Show only specified field IDs in answers |
| `answered_fields` | array | — | Filter to responses containing specified fields |

**Response Schema:**

```json
{
  "total_items": 100,
  "page_count": 4,
  "items": [
    {
      "response_id": "string",
      "token": "string",
      "landed_at": "2024-01-01T00:00:00Z",
      "landing_id": "string",
      "submitted_at": "2024-01-01T00:05:00Z",
      "answers": [
        {
          "type": "text|email|number|boolean|date|choice|choices|file_url",
          "field": {
            "id": "string",
            "ref": "string",
            "type": "string"
          },
          "text": "string",
          "email": "string",
          "number": 0,
          "boolean": true,
          "date": "2024-01-01",
          "choice": { "label": "string" },
          "choices": { "labels": ["string"] },
          "file_url": "string"
        }
      ],
      "calculated": { "score": 0 },
      "hidden": {},
      "variables": [
        { "key": "string", "type": "string", "text": "string", "number": 0 }
      ],
      "metadata": {
        "user_agent": "string",
        "referer": "string",
        "browser": "string",
        "platform": "string",
        "network_id": "string"
      }
    }
  ]
}
```

**Answer type mapping:**

| Answer Type | Field Types |
|---|---|
| `text` | short_text, long_text, dropdown |
| `email` | email |
| `number` | number, rating, opinion_scale, nps |
| `boolean` | yes_no, legal |
| `date` | date |
| `choice` | single selection from multiple_choice, picture_choice |
| `choices` | multiple selection from multiple_choice, picture_choice, ranking |
| `file_url` | file_upload |

---

### 3.2 Delete Responses

**`DELETE /forms/{form_id}/responses`**

Deletion is asynchronous — `200` indicates the request was registered, not that deletion is complete.

**Query parameter:** `included_response_ids` (string) — comma-separated response IDs, max 1000

**Request body alternative:** `included_response_ids` (array of string)

Response IDs not found are silently ignored. Verify deletion via the Retrieve Responses endpoint.

---

## 4. Error Responses

All APIs return error objects with this structure:

```json
{
  "code": "string",
  "description": "string",
  "details": []
}
```

| Status | Meaning |
|---|---|
| 400 | Bad Request — invalid parameters |
| 401 | Unauthorized — authentication failed |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource doesn't exist |
| 405 | Method Not Allowed |
| 409 | Conflict |
| 429 | Rate Limited — exceeded 2 req/sec |
| 500 | Internal Server Error |

---

## 5. Pagination

All list endpoints use consistent pagination:

- `page` (integer, default `1`) — page number
- `page_size` (integer) — results per page (defaults and maximums vary by endpoint)
- Response includes `total_items` and `page_count`

Responses API additionally supports cursor-based pagination via `after` and `before` tokens.

---

## 6. Webhooks API

### Overview

Webhooks deliver form response data to a URL immediately on submission. Response data is still stored on Typeform's servers and accessible via the Responses API.

**Rate limits:** None for webhooks.

**Timeout:** Webhooks must respond within 30 seconds.

**Retry policy:**

| Response Code | Behavior |
|---|---|
| `410 Gone` or `404 Not Found` | No retry; webhook disabled immediately |
| `429`, `408`, `503`, `423` | Retry every 2–3 minutes for 10 hours |
| Other error codes | Five retries with backoff: 5 min, 10 min, 20 min, 1 hr, 2 hrs, 3 hrs, 4 hrs |

**Auto-disable:** Webhooks disabled if 100% failure rate within 24 hours (300+ attempts) or 5 minutes (100+ attempts).

---

### 6.1 Create or Update Webhook

**`PUT /forms/{form_id}/webhooks/{tag}`**

Creates a new webhook or updates an existing one. Returns `200`.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `form_id` | string | Yes | Form identifier |
| `tag` | string | Yes | Unique webhook identifier/name |

**Request Body:**

| Field | Type | Description |
|---|---|---|
| `enabled` | boolean | Whether to send responses immediately |
| `event_types` | object | Event types triggering this webhook |
| `secret` | string | HMAC SHA256 signing secret for payload verification |
| `url` | string | Webhook destination URL |
| `verify_ssl` | boolean | Whether to verify SSL certificates |

**Event types object:**

```json
{
  "form_response": true,
  "form_response_partial": true
}
```

**Response:**

```json
{
  "created_at": "2016-11-21T12:23:28.000Z",
  "enabled": true,
  "event_types": { "form_response": true, "form_response_partial": true },
  "form_id": "abc123",
  "id": "yRtagDm8AT",
  "tag": "phoenix",
  "updated_at": "2016-11-21T12:23:28.000Z",
  "url": "https://test.com",
  "verify_ssl": true
}
```

---

### 6.2 Retrieve All Webhooks

**`GET /forms/{form_id}/webhooks`**

Returns `200` with `items` array of webhook objects (same schema as create/update response, plus optional `secret` field).

---

### 6.3 Retrieve Single Webhook

**`GET /forms/{form_id}/webhooks/{tag}`**

Returns `200` with a single webhook object.

---

### 6.4 Delete Webhook

**`DELETE /forms/{form_id}/webhooks/{tag}`**

Returns `204 No Content` on success. Returns `404` if webhook or form not found.

---

### 6.5 Webhook Payload Structure

Full payload delivered on `form_response` event:

```json
{
  "event_id": "LtWXD3crgy",
  "event_type": "form_response",
  "form_response": {
    "form_id": "lT4Z3j",
    "token": "a3a12ec67a1365927098a606107fac15",
    "response_url": "https://admin.typeform.com/form/lT4Z3j/results?responseId=...",
    "submitted_at": "2018-01-18T18:17:02Z",
    "landed_at": "2018-01-18T18:07:02Z",
    "calculated": { "score": 9 },
    "variables": [
      { "key": "score", "type": "number", "number": 4 },
      { "key": "name", "type": "text", "text": "typeform" }
    ],
    "hidden": { "user_id": "abc123456" },
    "definition": {
      "id": "lT4Z3j",
      "title": "Webhooks example",
      "fields": [
        {
          "id": "DlXFaesGBpoF",
          "title": "Question text...",
          "type": "long_text",
          "ref": "readable_ref_long_text",
          "allow_multiple_selections": false,
          "allow_other_choice": false
        }
      ],
      "endings": [
        {
          "id": "dN5FLyFpCMFo",
          "ref": "01GRC8GR2017M6WW347T86VV39",
          "title": "Bye!",
          "type": "thankyou_screen",
          "properties": {
            "button_text": "Create a typeform",
            "show_button": true,
            "share_icons": true,
            "button_mode": "default_redirect"
          }
        }
      ]
    },
    "answers": [
      {
        "type": "text",
        "text": "Answer text...",
        "answer_url": "https://admin.typeform.com/form/.../responses",
        "field": { "id": "DlXFaesGBpoF", "type": "long_text" }
      },
      {
        "type": "email",
        "email": "laura@example.com",
        "field": { "id": "SMEUb7VJz92Q", "type": "email" }
      },
      {
        "type": "choice",
        "choice": { "id": "4WIlUvKOl0UB", "label": "London", "ref": "..." },
        "field": { "id": "k6TP9oLGgHjl", "type": "multiple_choice" }
      },
      {
        "type": "choices",
        "choices": {
          "ids": ["eXnU3oA141Cg", "aTZmZGYV6liX"],
          "labels": ["London", "Sydney"],
          "refs": ["238d1802-...", "d867c542-..."]
        },
        "field": { "id": "PNe8ZKBK8C2Q", "type": "picture_choice" }
      },
      {
        "type": "boolean",
        "boolean": true,
        "field": { "id": "gFFf3xAkJKsr", "type": "legal" }
      },
      {
        "type": "number",
        "number": 5,
        "field": { "id": "Q7M2XAwY04dW", "type": "number" }
      },
      {
        "type": "date",
        "date": "2005-10-15",
        "field": { "id": "KoJxDM3c6x8h", "type": "date" }
      },
      {
        "type": "url",
        "url": "https://calendly.com/scheduled_events/...",
        "field": { "id": "M5tXK5kG7IeA", "type": "calendly" }
      }
    ],
    "ending": { "id": "dN5FLyFpCMFo", "ref": "01GRC8GR2017M6WW347T86VV39" }
  }
}
```

**Webhook answer types:** `text`, `email`, `number`, `boolean`, `date`, `choice`, `choices`, `url`, `file_url`

---

### 6.6 Webhook Security

Typeform signs payloads with HMAC SHA256. The signature is sent in the `Typeform-Signature` header.

**Verification process:**

1. Extract the full payload as binary data
2. Create HMAC-SHA256 hash using your secret as key
3. Base64-encode the hash
4. Prepend `sha256=`
5. Compare against `Typeform-Signature` header (use constant-time comparison)

**Python example:**

```python
import hashlib, hmac, base64, os

def verify_signature(received_signature, payload):
    secret = os.environ.get('TYPEFORM_SECRET_KEY')
    digest = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).digest()
    expected = 'sha256=' + base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, received_signature)
```

**Node.js example:**

```javascript
const crypto = require('crypto')
const verifySignature = (receivedSignature, payload) => {
  const hash = crypto
    .createHmac('sha256', process.env.SECRET_TOKEN)
    .update(payload)
    .digest('base64')
  return receivedSignature === `sha256=${hash}`
}
```

**Security notes:** Use HTTPS endpoints. SSL certificates must be valid (no self-signed). Use constant-time comparison to prevent timing attacks.

---

## 7. Embed SDK

### Overview

Client-side JavaScript library (`@typeform/embed`) for embedding typeforms into websites. Also available as React components (`@typeform/embed-react`).

**Security constraint:** Typeforms can only be embedded in HTTPS pages, HTTP localhost, or wrapped PWAs (enforced via CSP headers).

---

### 7.1 Installation

**NPM (vanilla):**

```bash
npm install --save @typeform/embed
```

**NPM (React):**

```bash
npm install --save @typeform/embed-react
```

**CDN:**

```html
<script src="//embed.typeform.com/next/embed.js"></script>
```

---

### 7.2 Embed Types

| Type | Vanilla Function | React Component | Description |
|---|---|---|---|
| Widget | `createWidget()` | `<Widget>` | Inline embed in page content |
| Popup | `createPopup()` | `<PopupButton>` | Full-screen modal |
| Slider | `createSlider()` | `<SliderButton>` | Side-sliding panel |
| Popover | `createPopover()` | `<Popover>` | Floating button with form |
| Sidetab | `createSidetab()` | `<Sidetab>` | Fixed side tab |

**Vanilla usage:**

```javascript
import { createWidget } from '@typeform/embed'
import '@typeform/embed/build/css/widget.css'
createWidget('<form-id>', { container: document.querySelector('#form') })
```

**React usage:**

```jsx
import { Widget } from '@typeform/embed-react'
const MyForm = () => <Widget id="<form-id>" style={{ width: '50%' }} />
```

**HTML data attributes:**

```html
<div data-tf-widget="<form-id>"></div>
<script src="//embed.typeform.com/next/embed.js"></script>
```

---

### 7.3 Configuration Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `container` | HTMLElement | — | Target element (required for widget) |
| `position` | string | `right` | Slider position: `right` or `left` |
| `size` | number | `100` | Popup size as percentage |
| `width` | number/string | — | Embed width |
| `height` | number/string | — | Embed height |
| `hidden` | object | — | Hidden fields passed via URL hash |
| `tracking` | object | — | Tracking parameters in query string |
| `hubspot` | boolean | `false` | HubSpot source tracking |
| `domain` | string | `https://form.typeform.com` | Environment domain |
| `source` | string | window domain | Host site domain |
| `medium` | string | `embed-sdk` | Plugin name |
| `mediumVersion` | string | `next` | Plugin version |
| `transitiveSearchParams` | string[] | — | Search params forwarded to form |
| `hideFooter` | boolean | `false` | Hide progress bar and nav buttons |
| `hideHeaders` | boolean | `false` | Hide question group headers |
| `opacity` | number | `100` | Background opacity (0–100) |
| `autoFocus` | boolean | `false` | Auto-focus on load |
| `open` | string | — | Auto-open trigger: `load`, `exit`, `scroll`, `time` |
| `openValue` | number | — | Trigger value (scroll %, ms delay, exit sensitivity) |
| `preventReopenOnClose` | boolean | `false` | Prevent re-opening after close |
| `enableSandbox` | boolean | `false` | Sandbox mode (no submissions recorded) |
| `buttonText` | string | `Launch me` | Sidetab button text |
| `customIcon` | string | — | Custom icon (URL, text, emoji, HTML) |
| `tooltip` | string | — | Tooltip text (popover only) |
| `notificationDays` | number | — | Red dot display duration in days |
| `autoClose` | number/boolean | — | Auto-close delay (ms) after submit |
| `autoResize` | string/boolean | `false` | Auto-resize to question height (widget; `"min,max"`) |
| `shareGaInstance` | string/boolean | `false` | Share Google Analytics instance |
| `inlineOnMobile` | boolean | `false` | Inline on mobile instead of fullscreen |
| `iframeProps` | object | — | HTML attributes for iframe |
| `buttonProps` | object | — | HTML attributes for button |
| `lazy` | boolean | `false` | Lazy loading (widget only) |
| `keepSession` | boolean | `false` | Preserve form state on close/reopen |
| `redirectTarget` | string | `_parent` | Redirect target: `_self`, `_top`, `_blank`, `_parent` |
| `disableScroll` | boolean | `false` | Disable scroll navigation |
| `preselect` | object | — | Pre-select first question answer |
| `respectOpenModals` | string | — | Modal conflict prevention: `all` or `same` |
| `region` | string | — | Account region: `eu` or `us` |

**HTML attribute conversion:** camelCase to `data-tf-` with dashes. Boolean = presence only. Objects = `key=value` pairs. Arrays = comma-separated.

---

### 7.4 Auto-Open Triggers

| Trigger | `open` | `openValue` |
|---|---|---|
| Page load | `load` | — |
| Exit intent | `exit` | Pixel sensitivity threshold |
| Scroll | `scroll` | Percentage (0–100) |
| Time delay | `time` | Milliseconds |

---

### 7.5 URL Parameters (Hidden Fields)

Pass data to forms via `hidden` config or `data-tf-hidden` attribute:

```javascript
createWidget('<form-id>', {
  container: document.getElementById('wrapper'),
  hidden: { full_name: 'John Doe', email: 'john@example.com' }
})
```

```html
<div data-tf-widget="<form-id>" data-tf-hidden="full_name=John Doe,email=john@example.com"></div>
```

**Transitive params** forward host page query params to the form:

```javascript
createWidget('<form-id>', {
  transitiveSearchParams: ['full_name', 'email']
})
```

---

### 7.6 Callbacks

All callbacks receive `{ formId }` at minimum.

| Callback | Payload | Fires When |
|---|---|---|
| `onReady` | `{ formId }` | Form finishes loading |
| `onStarted` | `{ formId, responseId }` | Submission starts |
| `onSubmit` | `{ formId, responseId }` | Form submitted (success only) |
| `onClose` | `{ formId }` | Modal window closes |
| `onQuestionChanged` | `{ formId, ref }` | Respondent navigates between questions |
| `onHeightChanged` | `{ formId, ref, height }` | Displayed question height changes |
| `onEndingButtonClick` | `{ formId }` | Ending screen button clicked (disables redirect) |
| `onDuplicateDetected` | `{ formId }` | Response quota reached (duplicate prevention) |

**JavaScript:**

```javascript
createPopup('<form-id>', {
  onSubmit: ({ formId, responseId }) => {
    console.log(`Form ${formId} submitted, response: ${responseId}`)
  }
})
```

**HTML:**

```html
<button data-tf-popup="<form-id>" data-tf-on-submit="handleSubmit">open</button>
<script>
  function handleSubmit({ formId, responseId }) {
    console.log(`Submitted: ${responseId}`)
  }
</script>
```

**Note:** HTML callbacks must be on the global `window` object.

---

### 7.7 React Programmatic Control

Use `embedRef` for programmatic open/close:

```jsx
const ref = useRef()
<PopupButton id="<form-id>" embedRef={ref}>open</PopupButton>
// Later: ref.current?.open()
```

---

## 8. JavaScript SDK (`@typeform/api-client`)

Official JS/TS client wrapper for the Typeform API. Source: [github.com/Typeform/js-api-client](https://github.com/Typeform/js-api-client).

### Installation

```bash
npm install @typeform/api-client
# or
yarn add @typeform/api-client
```

**Requirements:** Node.js >= 24. Single runtime dependency: `axios ^1.13.4`.

### Client Initialization

```typescript
import { createClient } from '@typeform/api-client'

// Standard
const tf = createClient({ token: '<your-token>' })

// EU Data Center (pre-August 2025 accounts)
const tf = createClient({ token: '<your-token>', apiBaseUrl: 'https://api.eu.typeform.com' })

// EU Data Center (August 2025+ accounts)
const tf = createClient({ token: '<your-token>', apiBaseUrl: 'https://api.typeform.eu' })

// No token (for endpoints that don't require auth)
const tf = createClient()
```

The client constructor wraps `axios` with bearer token auth and returns an object with these resource namespaces: `forms`, `images`, `themes`, `workspaces`, `responses`, `webhooks`, `insights`.

Default base URL: `https://api.typeform.com`.

### HTTP Client Internals

The internal `clientConstructor` builds each request by combining:
- Base URL (configurable via `apiBaseUrl` or defaults to `https://api.typeform.com`)
- Bearer token authorization header (when token provided)
- Custom headers from client args merged with per-request headers
- Query parameters built from a `params` object (null/undefined values filtered out)

Error handling: Axios errors are caught and re-thrown as `Typeform.ApiError(code, description, details)` extracted from `error.response.data`.

### Rate Limiting

Built-in rate limiter: 500ms delay between paginated requests (enforced during auto-pagination). This aligns with Typeform's 2 requests/second/account limit.

```typescript
// Internal implementation
const rateLimit = () => new Promise((resolve) => setTimeout(resolve, 500))
```

### Auto-Pagination

Three resource types support `page: "auto"`:
- **Forms** and **Workspaces**: Uses page-number pagination with `MAX_PAGE_SIZE = 200`. Recursively fetches pages until `items.length < MAX_PAGE_SIZE`.
- **Themes**: Same page-number pagination pattern, `MAX_PAGE_SIZE = 200`.
- **Responses**: Uses cursor-based pagination with `MAX_RESULTS_PAGE_SIZE = 1000`. Uses the last `response_id` as the `before` cursor for subsequent pages.

All auto-pagination functions include rate limiting between requests.

### Forms

```typescript
tf.forms.list({ page?, pageSize?, search?, workspaceId? })
tf.forms.get({ uid })
tf.forms.create({ data })
tf.forms.update({ uid, data, override? })
tf.forms.delete({ uid })
tf.forms.copy({ uid, workspaceHref? })
tf.forms.messages.get({ uid })
tf.forms.messages.update({ uid, data })
```

**`forms.list()`** — Retrieve forms with optional filtering.
- `page`: Page number or `"auto"` for all pages
- `pageSize`: Results per page (default 10)
- `search`: Filter by string match
- `workspaceId`: Filter by workspace

**`forms.get({ uid })`** — Retrieve a single form by UID.

**`forms.create({ data })`** — Create a new form. `data` is a `Typeform.Form` object.

**`forms.update({ uid, data, override? })`** — Two modes:
- `override: true` → `PUT /forms/{uid}` — replaces entire form. `data` is a full `Typeform.Form`.
- `override: false` (default) → `PATCH /forms/{uid}` — partial update. `data` is an array of patch operations.

Supported PATCH paths:
```
/settings/facebook_pixel
/settings/google_analytics
/settings/google_tag_manager
/settings/is_public
/settings/meta
/cui_settings
/theme
/title
/workspace
```

Patch operation format:
```typescript
{ op: 'add' | 'remove' | 'replace', path: string, value: any }
```

**`forms.delete({ uid })`** — Delete a form.

**`forms.copy({ uid, workspaceHref? })`** — Copies a form by fetching it, stripping `id` and `integrations` keys (recursively), and creating a new form. Optionally assigns to a different workspace via `workspaceHref`.

**`forms.messages.get({ uid })`** — Retrieve custom form messages.

**`forms.messages.update({ uid, data })`** — Update custom messages via `PUT`. `data` is a `Typeform.Messages` object.

### Images

```typescript
tf.images.list()
tf.images.get({ id, size?, backgroundSize?, choiceSize? })
tf.images.add({ image?, url?, fileName })
tf.images.delete({ id })
```

**`images.get()`** — Retrieve image with optional size variant. Only one size parameter should be specified:
- `size`: `"default"` | `"thumbnail"` | `"mobile"` → URL: `/images/{id}/image/{size}`
- `backgroundSize`: `"default"` | `"thumbnail"` | `"mobile"` | `"tablet"` → URL: `/images/{id}/background/{size}`
- `choiceSize`: `"default"` | `"thumbnail"` | `"supersize"` | `"supermobile"` | `"supersizefit"` | `"supermobilefit"` → URL: `/images/{id}/choice/{size}`

**`images.add()`** — Upload via base64 `image` string or `url`. `fileName` is required.

### Themes

```typescript
tf.themes.list({ page?, pageSize? })
tf.themes.get({ id })
tf.themes.create({ name, colors, font, background?, hasTransparentButton?, fields?, screens?, roundedCorners? })
tf.themes.update({ id, name, colors, font, background?, hasTransparentButton?, fields?, screens?, roundedCorners? })
tf.themes.delete({ id })
```

**Required properties for create/update:** `name`, `colors`, `font`. Font is validated against the allowed fonts list (see Type Definitions below).

Theme create uses `POST /themes`; update uses `PUT /themes/{id}`.

Property mapping (SDK → API):
- `hasTransparentButton` → `has_transparent_button`
- `roundedCorners` → `rounded_corners`

**`ThemeColors`**: `{ answer, background, button, question }` — all hex strings.

**`ThemeFontSizeAndAlignment`**: `{ alignment: 'left' | 'center', font_size: 'small' | 'medium' | 'large' }` — applies to both `fields` and `screens`.

**`ThemeRoundedCorners`**: `'none'` | `'small'` | `'large'`

**`ThemeBackground`**: `{ href, layout: 'fullscreen' | 'repeat' | 'no-repeat', brightness: -1..1 }`

### Workspaces

```typescript
tf.workspaces.list({ search?, page?, pageSize? })
tf.workspaces.get({ id })
tf.workspaces.add({ name })
tf.workspaces.update({ id, data })
tf.workspaces.delete({ id })
tf.workspaces.addMembers({ id, members })
tf.workspaces.removeMembers({ id, members })
```

**`workspaces.list()`** — Supports `page: "auto"`. `search` filters by name match.

**`workspaces.add({ name })`** — Creates a workspace. Name is required (throws if missing).

**`workspaces.update({ id, data })`** — Sends `PATCH /workspaces/{id}`. `data` is an array of patch operations with paths `/name` or `/members`.

**`workspaces.addMembers()`** / **`removeMembers()`** — Convenience methods that build patch operations from email strings/arrays:
```typescript
// Internally generates:
[{ op: 'add', path: '/members', value: { email: 'user@example.com' } }]
```

### Responses

```typescript
tf.responses.list({ uid, pageSize?, since?, until?, after?, before?, ids?, completed?, sort?, query?, fields?, page? })
tf.responses.delete({ uid, ids })
```

**`responses.list()`** — Full-featured response retrieval with filtering.
- `uid`: Form UID (required)
- `pageSize`: Max 1000
- `since` / `until`: ISO 8601 date filters
- `after` / `before`: Cursor-based pagination tokens (response IDs)
- `ids`: Filter to specific response IDs (string or string array → comma-separated)
- `completed`: Boolean filter for submission status
- `sort`: Sort order (default: `submitted_at,desc`)
- `query`: Full-text search (includes Hidden Fields)
- `fields`: Limit to specific field IDs (string or string array → comma-separated)
- `page: "auto"`: Auto-paginate all responses using cursor-based pagination with max page size 1000

**`responses.delete()`** — Delete responses by token IDs. `ids` accepts string or string array (up to 1000), sent as `included_tokens` query parameter.

### Webhooks

```typescript
tf.webhooks.list({ uid })
tf.webhooks.get({ uid, tag })
tf.webhooks.create({ uid, tag, url, enabled?, secret?, verifySSL? })
tf.webhooks.update({ uid, tag, url, enabled?, secret?, verifySSL? })
tf.webhooks.delete({ uid, tag })
tf.webhooks.toggle({ uid, tag, enabled })
```

Both `create` and `update` use `PUT /forms/{uid}/webhooks/{tag}` (idempotent upsert). Validation: `url` and `tag` are required (throws if missing). `enabled` defaults to `false`. `verifySSL` maps to `verify_ssl` in the API payload (only sent when truthy).

**`webhooks.toggle()`** — Sends `PUT` with only `{ enabled }` in the body to quickly enable/disable.

### Insights

```typescript
tf.insights.summary({ uid })
```

**`insights.summary()`** — Returns form-level and field-level insights via `GET /insights/{uid}/summary`.

Response structure:
```typescript
{
  fields: [{
    id, ref, title, type,
    dropoffs: number,  // respondents who abandoned at this field
    views: number      // respondents who saw this field
  }],
  form: {
    platforms: [{
      platform: 'desktop' | 'phone' | 'tablet' | 'other',
      average_time, completion_rate, responses_count, total_visits, unique_visits
    }],
    summary: {
      average_time, completion_rate, responses_count, total_visits, unique_visits
    }
  }
}
```

### Type Definitions Reference

#### Field Types

```
address | calendly | contact_info | date | dropdown | email | file_upload |
group | legal | long_text | matrix | multiple_choice | nps | number |
opinion_scale | payment | phone_number | picture_choice | ranking | rating |
short_text | statement | website | yes_no
```

#### Available Fonts

```
Acme | Arial | Arvo | Avenir Next | Bangers | Cabin | Cabin Condensed |
Courier | Crete Round | Dancing Script | Exo | Georgia | Handlee |
Helvetica Neue | Karla | Lato | Lekton | Lobster | Lora | McLaren |
Montserrat | Nixie One | Old Standard TT | Open Sans | Oswald |
Playfair Display | Quicksand | Raleway | Signika | Sniglet |
Source Sans Pro | Vollkorn
```

#### Supported Languages

```
en | es | ca | fr | de | ru | it | da | pt | ch | zh | nl | no | uk |
ja | ko | hr | fi | sv | pl | el | hu | tr | cs | et | di
```

#### Answer Types (in responses)

```
choice | choices | date | email | url | file_url | number | boolean |
text | payment | phone_number
```

#### Logic Jump Condition Operators

```
begins_with | ends_with | contains | not_contains | lower_than |
lower_equal_than | greater_than | greater_equal_than | is | is_not |
equal | not_equal | always | on | not_on | earlier_than |
earlier_than_or_on | later_than | later_than_or_on
```

Compound conditions use `and` / `or` operators with nested `vars` arrays.

#### Logic Jump Actions

```
jump | add | subtract | multiply | divide
```

Target types: `field` | `hidden` | `thankyou`. Variable targets: `score` | `price`.

#### Form Settings

| Property | Type | Description |
|---|---|---|
| `is_public` | boolean | Form visibility |
| `progress_bar` | `'percentage'` \| `'proportion'` | Progress indicator type |
| `show_progress_bar` | boolean | Display progress bar |
| `show_typeform_branding` | boolean | Display Typeform branding (PRO+) |
| `show_time_to_complete` | boolean | Auto-calculated time estimate on welcome screen |
| `show_number_of_submissions` | boolean | Submission count on welcome screen (mutually exclusive with time estimate) |
| `show_question_number` | boolean | Question numbers on blocks |
| `show_key_hint_on_choices` | boolean | Key hint letters on choice blocks |
| `show_cookie_consent` | boolean | Cookie consent banner |
| `hide_navigation` | boolean | Hide navigation arrows |
| `free_form_navigation` | boolean | Allow free navigation between questions |
| `autosave_progress` | boolean | Client-side partial response saving |
| `are_uploads_public` | boolean | File upload visibility |
| `redirect_after_submit_url` | string | Post-submission redirect URL |
| `google_analytics` | string | GA tracking ID |
| `facebook_pixel` | string | Facebook Pixel ID |
| `google_tag_manager` | string | GTM ID |
| `meta.allow_indexing` | boolean | Search engine indexing |
| `meta.description` | string | SEO description |
| `meta.image.href` | string | SEO image URL |

#### Custom Messages Keys

The `Messages` interface defines 40+ customizable UI strings. Key categories:

- **Button labels**: `label.button.submit`, `label.button.ok`, `label.button.review`, `label.buttonNoAnswer.default`, `label.buttonHint.default`, `label.buttonHint.longtext`
- **Error messages**: `label.error.required`, `label.error.mustEnter`, `label.error.mustSelect`, `label.error.emailAddress`, `label.error.url`, `label.error.server`, `label.error.incompleteForm`, `label.error.maxValue`, `label.error.minValue`, `label.error.range`, `label.error.maxLength`, `label.error.sizeLimit`, `label.error.mustAccept`, `label.error.expiryMonthTitle`, `label.error.expiryYearTitle`
- **Progress**: `label.progress.percent` (accepts `progress:percent`), `label.progress.proportion` (accepts `progress:step`, `progress:total`)
- **Field-specific**: `block.shortText.placeholder`, `block.longtext.hint`, `block.dropdown.placeholder`, `block.dropdown.placeholderTouch`, `block.dropdown.hint`, `block.multipleChoice.hint`, `block.multipleChoice.other`, `block.legal.accept`, `block.legal.reject`, `block.fileUpload.choose`, `block.fileUpload.drag`, `block.fileUpload.uploadingProgress`
- **Payment**: `block.payment.cardNameTitle`, `block.payment.cardNumberTitle`, `block.payment.cvcDescription`, `block.payment.cvcNumberTitle`
- **Yes/No**: `label.yes.default`, `label.yes.shortcut`, `label.no.default`, `label.no.shortcut`
- **Other**: `label.warning.connection`, `label.warning.correction`, `label.warning.fallbackAlert`, `label.warning.formUnavailable`, `label.warning.success`, `label.hint.key`, `label.preview`, `label.action.share`

Message formatting: `*bold*` and `_italic_` are supported. HTML tags are forbidden. Most have character limits (28–128 characters depending on field).

#### Notification Settings

Nested under `settings.notification`:

- **`self`** (admin notifications): `enabled`, `recipients[]`, `reply_to`, `subject`, `message`
- **`respondent`** (respondent notifications): `enabled`, `recipient`, `reply_to[]`, `subject`, `message`

Recall Information variables available: `{{form:title}}`, `{{account:email}}`, `{{account:name}}`, `{{account:fullname}}`, `{{link:report}}`, `{{form:all_answers}}`, `{{field:ref}}`, `{{hidden:ref}}`

#### Image Types

Supported media types: `image/gif`, `image/jpeg`, `image/png`.

Image object properties: `id`, `src`, `file_name`, `width`, `height`, `media_type`, `has_alpha`, `avg_color`.

#### Attachment Object

Used on welcome screens, thank you screens, and most field types:
```typescript
{
  type: 'image' | 'video',
  href: string,        // Typeform image URL or YouTube URL
  scale?: 0.4 | 0.6 | 0.8 | 1  // video only, default 0.6
}
```

#### Currency Options (Payment Fields)

```
AUD | BRL | CAD | CHF | DKK | EUR | GBP | MXN | NOK | SEK | USD
```

### CLI Usage

The SDK includes a CLI binary (`typeform-api`):

```bash
# Set token
export TF_TOKEN=tfp_XXXXXXXXXX

# Usage
yarn typeform-api <method> [params]

# Examples
yarn typeform-api forms.list
yarn typeform-api forms.get '{uid:"abcd1234"}'
yarn typeform-api themes.list '{pageSize:3}'
```

### Error Handling

All API errors are thrown as `Typeform.ApiError`:

```typescript
class ApiError extends Error {
  code: string       // Error code from API
  details: Object[]  // Additional error details
}
```

Default error description: `"Couldn't make request"` (when `error.response.data` is unavailable).
