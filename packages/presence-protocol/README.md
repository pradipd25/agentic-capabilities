# Presence Protocol

**Version: `0.1.0` (alpha — expect breakage until 1.0)**

The transport-agnostic contract at the heart of the "give any agent a face"
framework. It is a normalized event vocabulary that decouples *where the agent
runs* (the **adapter**) from *the face that represents it* (the **renderer**).

```
 agent source ──adapter──▶ [ Presence Protocol ] ──▶ renderer (the face)
```

Any adapter (Claude Agent SDK, MCP, OpenAI, raw stream) translates a source's
native events into this protocol; any renderer consumes it. That is what makes
the framework *any-agent*.

The protocol is **bidirectional**:

- **Downstream** — agent → face: `PresenceEvent`s describing what the agent is doing.
- **Upstream** — face → agent: `ControlMessage`s carrying user input and control.

The transport (WebSocket today; MCP / SSE later) carries both; this package only
defines the *schema* and a conformance validator. Source of truth lives here and
is published for both TypeScript (`./typescript`) and Python (`./python`).

---

## Downstream — `PresenceEvent` (agent → face)

| `type` | Purpose | Key fields | Renderer behavior |
|---|---|---|---|
| `session_ready` | session established | `session_id`, `protocol_version`, `avatar?`, `available_avatars`, `voice_id?` | init UI |
| `avatar_state` | animation state | `animation` (idle/listening/thinking/talking/greeting), `speaking`, `audio_level?` | drive pose |
| `speak_delta` | streamed conversational text token | `text` | chat bubble + **TTS** |
| `transcript` | finalized line | `speaker` (user/assistant), `text` | transcript log |
| `think` | reasoning / working | `text?` | "thinking" pose; fill pauses |
| `action` | a tool/step the agent took | `name`, `detail?`, `input?`, `status` (start/success/error), `id?` | **action chip — never spoken** |
| `ask` | clarification / approval | `id`, `question`, `kind` (clarify/approve), `options?` | confirm UX |
| `status` | progress / heartbeat | `text?`, `progress?` | keep avatar alive |
| `avatar_changed` | avatar swapped | `avatar` | swap model |
| `voice_changed` | voice swapped | `voice_id`, `reconnect_required` | apply voice |
| `error` | error surfaced | `message`, `code?` | surface |
| `done` | turn finished | `full_text?`, `cost_usd?`, `duration_ms?`, `turns?` | back to idle |

**The speech-vs-action split is part of the contract:** conversational text
(`speak_delta` / `transcript`) is spoken via TTS; tool activity (`action`) is shown
visually and **never read aloud**.

## Upstream — `ControlMessage` (face → agent)

| `type` | Purpose | Key fields |
|---|---|---|
| `user_turn` | user said/typed something | `text` |
| `interrupt` | barge-in / cancel current turn | — |
| `ask_response` | answer to an `ask` | `id`, `value` |
| `set_avatar` | switch character | `avatar_id` |
| `set_voice` | switch voice | `voice_id` |

---

## Migration from the v0 app wire format

The reference app currently emits an ad-hoc set of messages. The mapping to v0.1:

| v0 app message | v0.1 protocol event |
|---|---|
| `llm_token` `{token}` | `speak_delta` `{text}` |
| `llm_done` `{full_text}` | `done` `{full_text}` |
| `transcript_final` `{speaker,text}` | `transcript` `{speaker,text}` |
| `voice_change_ack` `{voice_id,reconnect_required}` | `voice_changed` |
| `text_input` `{text}` (client→server) | `user_turn` `{text}` |
| `avatar_state`, `session_ready`, `avatar_changed`, `error`, `set_avatar`, `set_voice` | unchanged |

New in v0.1: `think`, `action`, `ask`, `status`, `interrupt`, `ask_response`.
</content>
