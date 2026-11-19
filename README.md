# VoltHabit

A sleek, pitch-black (`#09090B`) and electric neon-green (`#39FF14`) Android habit tracker built with **Jetpack Compose**, **Firebase Authentication (Google Sign-In)**, and **Cloud Firestore** real-time cross-device sync.

---

## Design Tokens

| Token | Hex | Usage |
|---|---|---|
| Pitch Black | `#09090B` | Primary screen canvas & launcher background |
| Dark Zinc | `#18181B` | Elevated habit cards, bottom bar, modals |
| Crisp White | `#FAFAFA` | Primary typography & active borders |
| Electric Neon Green | `#39FF14` | Glowing checkboxes, streaks, progress bars, peak heatmap tiles |

---

## Firebase Project Configuration (For External Native Widgets)

Connect external native widgets (Android Glance, iOS WidgetKit, macOS, or web companions) to this exact Firebase project and **named Firestore database**:

> **Important:** This backend provisions a **named Firestore Enterprise database**. Always pass the explicit `firestore_database_id` below instead of the `(default)` database.

```json
{
  "projectId": "gen-lang-client-0880363053",
  "projectNumber": "519428555142",
  "storageBucket": "gen-lang-client-0880363053.firebasestorage.app",
  "firestoreDatabaseId": "ai-studio-android-volthabi-49d89ac7-d707-4fd5-8572-478243a64893",
  "android": {
    "packageName": "com.aistudio.volthabit.qvxnkp",
    "mobileSdkAppId": "1:519428555142:android:4059bb43142109ca9c2c07"
  },
  "auth": {
    "provider": "Google Sign-In",
    "webOAuthClientId": "519428555142-997e7m076e6kb1dk2jfi7s0a3truikgm.apps.googleusercontent.com"
  }
}
```

### Connecting to the Named Firestore Database

#### Android (Kotlin)
```kotlin
val db = FirebaseFirestore.getInstance(
    "ai-studio-android-volthabi-49d89ac7-d707-4fd5-8572-478243a64893"
)
val habitsRef = db.collection("users").document(uid).collection("habits")
```

#### iOS / macOS (Swift — WidgetKit)
```swift
let db = Firestore.firestore(
    database: "ai-studio-android-volthabi-49d89ac7-d707-4fd5-8572-478243a64893"
)
let habitsRef = db.collection("users").document(uid).collection("habits")
```

#### Web / JavaScript SDK (v10+)
```js
import { initializeApp } from "firebase/app";
import { getFirestore, collection } from "firebase/firestore";

const app = initializeApp({
  projectId: "gen-lang-client-0880363053",
  storageBucket: "gen-lang-client-0880363053.firebasestorage.app",
  messagingSenderId: "519428555142",
});

const db = getFirestore(
  app,
  "ai-studio-android-volthabi-49d89ac7-d707-4fd5-8572-478243a64893"
);
const habitsRef = collection(db, "users", uid, "habits");
```

---

## Firestore Data Schema

**Collection Path:** `users/{userId}/habits/{habitId}`

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `title` | `string` | `1..120` chars | Display title of the habit |
| `frequency` | `string` | `"daily"` \| `"weekly"` | Tracking cadence |
| `completedDates` | `array<string>` | Max `3650` items, `YYYY-MM-DD` | Sorted unique completion date strings |
| `streak` | `integer` | `0..10000` | Current active streak count |
| `createdAt` | `timestamp` | `<= request.time`, immutable | Always submit `FieldValue.serverTimestamp()` on creation |

### Toggling Today from an External Widget
Send a partial `.update(...)` containing only `completedDates` and `streak` (never modify `createdAt` or add unknown keys):

```json
{
  "completedDates": ["2026-11-18", "2026-11-19"],
  "streak": 2
}
```

---

## Firestore Security Rules (`firestore.rules`)

```javascript
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    // Global default-deny safety net
    match /{document=**} {
      allow read, write: if false;
    }

    // --- Primitive Helpers ---
    function isSignedIn() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return isSignedIn() && request.auth.uid == userId;
    }

    function isValidId(id) {
      return id is string &&
             id.size() >= 1 &&
             id.size() <= 128 &&
             id.matches('^[a-zA-Z0-9_\\-]+$');
    }

    function incoming() {
      return request.resource.data;
    }

    function existing() {
      return resource.data;
    }

    // --- Entity Validation Blueprint ---
    function isValidDateString(value) {
      return value is string &&
             value.size() == 10 &&
             value.matches('^[0-9]{4}-[0-9]{2}-[0-9]{2}$');
    }

    function isValidHabit(data) {
      return data.keys().hasAll(['title', 'frequency', 'completedDates', 'streak', 'createdAt']) &&
             data.keys().hasOnly(['title', 'frequency', 'completedDates', 'streak', 'createdAt']) &&
             data.title is string &&
             data.title.size() >= 1 &&
             data.title.size() <= 120 &&
             data.frequency is string &&
             data.frequency.size() <= 10 &&
             data.frequency in ['daily', 'weekly'] &&
             data.completedDates is list &&
             data.completedDates.size() <= 3650 &&
             (data.completedDates.size() == 0 || (
               isValidDateString(data.completedDates[0]) &&
               isValidDateString(data.completedDates[data.completedDates.size() - 1])
             )) &&
             data.streak is int &&
             data.streak >= 0 &&
             data.streak <= 10000 &&
             data.createdAt is timestamp;
    }

    // --- User-Scoped Habits Collection ---
    match /users/{userId}/habits/{habitId} {
      // Single-document read enforces path ID validation and strict ownership
      allow get: if isSignedIn() &&
                    isValidId(userId) &&
                    isValidId(habitId) &&
                    isOwner(userId);

      // Subcollection list enforces ownership via path wildcard (no existing() check on empty lists)
      allow list: if isSignedIn() &&
                     isValidId(userId) &&
                     isOwner(userId);

      // Create enforces full schema, strict keyset, and server timestamp upper bound
      allow create: if isSignedIn() &&
                       isValidId(userId) &&
                       isValidId(habitId) &&
                       isOwner(userId) &&
                       isValidHabit(incoming()) &&
                       incoming().createdAt <= request.time;

      // Update validates projected post-write state, keeps createdAt immutable, and restricts to named actions
      allow update: if isSignedIn() &&
                       isValidId(userId) &&
                       isValidId(habitId) &&
                       isOwner(userId) &&
                       isValidHabit(incoming()) &&
                       incoming().createdAt == existing().createdAt && (
                         // Action 1: Toggle completion dates and recalculate streak
                         incoming().diff(existing()).affectedKeys().hasOnly(['completedDates', 'streak']) ||
                         // Action 2: Edit habit title/frequency (with optional streak recalculation)
                         incoming().diff(existing()).affectedKeys().hasOnly(['title', 'frequency', 'streak'])
                       );

      // Delete enforces strict ownership and path ID validation
      allow delete: if isSignedIn() &&
                       isValidId(userId) &&
                       isValidId(habitId) &&
                       isOwner(userId);
    }
  }
}
```

---

## VoltHabit Desktop Suite & Real-Time Companion (PyQt6)

A dual-mode desktop software for Windows featuring both a **Full Management Desktop Dashboard** and a **Lightweight Floating Desktop Widget**, fully synchronized in real time with your mobile app via Cloud Firestore (`users/{userId}/habits`).

### Key Features
1. **Full Desktop Dashboard (`open_dashboard.bat`)**:
   - 📋 **Habits Manager**: Add, edit, delete, and check off habits with full real-time bidirectional Firestore sync.
   - 📁 **Grouped Habits & Routines**: Organize habits by routine (`exercise`, `morning routine`, `deep work`, `night routine`). Batch-complete an entire routine with one click.
   - 🎯 **Long-Term Goals Tracker**: Set milestones and targets (e.g. *"50 Workout Days"*, *"Read 24 Books"*), track deadlines, increment progress with `+1` / `-1` buttons, and link daily habits so completing a habit automatically advances its associated goal.
   - 📊 **30-Day Activity Heatmap & Metrics**: Visual breakdown of your consistency, streak ranks, and completion rates.
   - 📌 **Instant Mode Switching**: Switch between the Full Dashboard and the Floating Desktop Widget with one click.

2. **Floating Desktop Widget (`run_widget.bat`)**:
   - **Theme**: Pitch-black (`#09090B`) semi-transparent rounded window (300px × 380px) with 1px neon-green (`#39FF14`) border, white text, glowing neon checkboxes, and electric streak badges (`⚡`).
   - **Desktop Pinning**: Pinned to the desktop layer (`WindowStaysOnBottomHint`) so it remains visible without covering full-screen games or applications.
   - **One-Click Expand**: Click `⤢` to open the full dashboard suite anytime.

3. **System Tray Integration**:
   - High-DPI neon bolt tray icon.
   - Right-click menu: *Open Full Dashboard*, *Show/Hide Widget*, *Pin to Desktop Layer*, *Sync Now*, and *Exit*.

4. **One-Click Windows Startup (`add_to_startup.bat`)**:
   - Adds the widget to Windows Startup (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\VoltHabitWidget.lnk`) to start silently on boot using `pythonw.exe`.


### Quick Start
1. Edit [.env](file:///c:/Users/Jyoti/Downloads/habttracker/.env) with your `FIREBASE_USER_ID` and credentials.
2. Double-click [run_widget.bat](file:///c:/Users/Jyoti/Downloads/habttracker/run_widget.bat) to launch the widget.
3. Double-click [add_to_startup.bat](file:///c:/Users/Jyoti/Downloads/habttracker/add_to_startup.bat) to enable auto-launch on PC boot.

