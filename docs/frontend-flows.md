# Frontend Application Workflows

This document summarizes the current user journeys from the frontend perspective. It is intended to present the product and help design and engineering understand which screens exist, which decisions each role makes, and where the most important UX moments occur.

## 1. Main Navigation Map

```mermaid
flowchart TD
    A["Home / Published events"] --> B["Event details"]
    B --> C{"One or multiple sessions?"}
    C -->|One session| D["Available tickets"]
    C -->|Multiple sessions| E["Visual date and venue selector"]
    E --> D
    D --> F["Ticket selection"]
    F --> G{"Authenticated user?"}
    G -->|Yes| H["Reserve with account data"]
    G -->|No| I["Guest buyer form"]
    I --> J["Accept terms and privacy policy"]
    H --> K["Order summary"]
    J --> K
    K --> L["Demo checkout"]
    L --> M{"Payment result"}
    M -->|Successful| N["Payment confirmation"]
    M -->|Failed or cancelled| O["Payment error"]
    N --> P["Email with PDF tickets"]
    N --> Q["Profile / My tickets"]
```

## 2. Buyer Workflow

```mermaid
flowchart TD
    A["Buyer opens the home page"] --> B["Views published event cards"]
    B --> C["Opens an event"]
    C --> D{"Published sessions available?"}
    D -->|No| E["Message: dates coming soon"]
    D -->|Yes| F{"Number of sessions"}
    F -->|One| G["Session details are displayed"]
    F -->|Multiple| H["Selects a session by venue and date"]
    H --> G
    G --> I["Views venue, address, date, and tickets"]
    I --> J["Selects quantities"]
    J --> K{"Authenticated?"}
    K -->|Yes| L["Continues with account details"]
    K -->|No| M["Enters name, confirmed email, and phone"]
    M --> N["Accepts terms"]
    L --> O["Temporarily reserves stock"]
    N --> O
    O --> P["Summary: tickets, fees, and total"]
    P --> Q["Completes the demo payment"]
    Q --> R["Returns to payment confirmation"]
    R --> S["Receives PDF tickets by email"]
    S --> T["Presents QR code at the venue"]
```

### Affected Screens

- `/`: published event listing.
- `/events/:eventId`: public event details.
- `/checkout/:orderId`: order summary and demo payment handoff.
- `/payment/demo`: self-contained payment confirmation.
- `/payment/success`: payment confirmation.
- `/payment/error`: failed or cancelled payment.
- `/profile`: account details.
- `/my-tickets`: purchased-ticket search and downloads.

## 3. Promoter Workflow

```mermaid
flowchart TD
    A["Promoter signs in"] --> B["Promoter workspace"]
    B --> C["Creates an event"]
    C --> D["Completes event-level details"]
    D --> E["Configures sessions"]
    E --> F["Creates sale groups"]
    F --> G["Creates session ticket types"]
    G --> H["Submits sessions for review"]
    H --> I["Session under review"]
    I --> J{"Administrator decision"}
    J -->|Changes requested| K["Session returns to not reviewed"]
    J -->|Cancelled| L["Session marked cancelled"]
    J -->|Approved| M["Session becomes draft"]
    K --> E
    M --> N["Event can be published"]
    N --> O["Administrator publishes approved sessions"]
    O --> P["Tickets become visible to buyers"]
    P --> Q["Promoter views sales, revenue, and invitations"]
    Q --> R["Requests validation stations"]
```

### Visible UX Rules

- While a session is under review, the promoter cannot edit it.
- Management information appears progressively: less before approval and more after publication.
- High-impact actions require confirmation: publishing, unpublishing, finishing, deleting, and cancelling a review.
- Finished sessions appear dimmed, at the end of the list, and without sales actions.
- Only administrators publish event and session content.

## 4. Administrator Workflow

```mermaid
flowchart TD
    A["Administrator signs in"] --> B["Top bar with review counter"]
    B --> C["Administrator review queue"]
    C --> D["Views pending events and sessions"]
    D --> E["Opens a request"]
    E --> F{"Decision"}
    F -->|Approve| G["Defines platform fee"]
    G --> H["Event or session returns to draft"]
    F -->|Request changes| I["Writes a reason"]
    I --> J["Promoter receives a notification"]
    F -->|Cancel| K["Writes an optional reason"]
    K --> L["Promoter receives a notification"]
    B --> M["User administration"]
    M --> N["Creates promoters"]
    M --> O["Super administrator creates administrators"]
    B --> P["Order support"]
    P --> Q["Searches by email, phone, name, or payment ID"]
    Q --> R["Corrects contact details or resends tickets"]
    B --> S["Validation requests"]
    S --> T["Approves station quota per session"]
```

### Affected Screens

- `/admin/reviews`: event and session review queue.
- `/admin/users`: users, promoters, administrators, and order support.
- `/admin/validation-requests`: validation-station requests.
- `/events/:eventId/manage`: complete event management.
- `/events/:eventId/manage/sessions/:sessionId`: session details and management.

## 5. Validator Workflow

```mermaid
flowchart TD
    A["Administrator or promoter creates a validation station"] --> B["Activation link is generated"]
    B --> C["Link is delivered to a device or operator"]
    C --> D["Validator opens the link"]
    D --> E["Activates the station"]
    E --> F["Opens the scanning screen"]
    F --> G["Opens the camera"]
    G --> H["Scans a QR code"]
    H --> I{"Result"}
    I -->|Valid| J["Green screen: ticket validated"]
    I -->|Already used| K["Red screen: ticket already validated"]
    I -->|Wrong session| L["Red screen: ticket belongs to another session"]
    I -->|Too early or late| M["Red screen: outside validation window"]
    I -->|Not found| N["Red screen: QR code not found"]
    J --> G
    K --> G
    L --> G
    M --> G
    N --> G
    F --> O["Records a manual incident"]
    O --> P["Activity is visible to administrators and promoters"]
```

### Affected Screens

- `/validator/activate`: station activation.
- `/validator/scan`: recurring QR scanning.
- `/validation-stations/:stationId/activity`: activity for a specific station.

## 6. Main Status Lifecycle

```mermaid
stateDiagram-v2
    [*] --> not_reviewed: Created
    not_reviewed --> in_review: Submit for review
    in_review --> not_reviewed: Request changes
    in_review --> cancelled: Cancel review
    in_review --> draft: Approve
    draft --> published: Publish
    published --> unpublished: Unpublish
    unpublished --> published: Republish
    published --> sold_out: Stock exhausted
    sold_out --> published: Stock available
    published --> finished: Finish
    sold_out --> finished: Finish
    draft --> archived: Delete or archive
    cancelled --> archived: Archive
```

## 7. Key UX Considerations

- The session selector presents venue, date, and time visually rather than showing only a date.
- When only one session exists, no selector is displayed.
- The address behaves as a link to Google Maps.
- The order summary stays simple: tickets, service fees, and total.
- Buying and validation receive absolute priority on mobile through large controls, legible text, and forms without clipping.
- Dangerous administrative actions use clear confirmation modals rather than native alerts.
- Statuses are clearly labelled and visually prioritized: under review, draft, published, finished, and cancelled.
- Loading and empty states preserve layout stability and avoid unnecessary shifts.
