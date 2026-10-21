# CC Switch Connection

SymmetryLab can use CC Switch's local Codex route. Configure your provider in CC Switch, enable Codex routing, and then select **CC Switch local routing** in the workbench. The preset is:

```json
{
  "base_url": "http://127.0.0.1:15721/v1",
  "protocol": "responses",
  "auth_mode": "cc_switch",
  "model": "SET_YOUR_MODEL"
}
```

Replace the model placeholder with an ID your selected provider supports. Base URL must exclude the final `/responses` path. If you changed the local routing port, use that port. The adapter sends a placeholder authorization value; CC Switch injects the upstream key. No configuration import or credential extraction occurs.

Click **Test connection** to send one small real request. A successful text response confirms endpoint/protocol connectivity; it does not guarantee structured agent behavior. Select **Live model research** afterward. Model providers should follow the JSON-action contract; malformed actions receive feedback and three consecutive errors stop the run.

## Troubleshooting

- **Connection failed:** confirm that the local routing service is running and Codex routing is enabled. Merely installing CC Switch or switching a direct provider does not start a route usable by SymmetryLab.
- **HTTP 400 / 404:** check model ID, Base URL and Responses protocol. The upstream format is selected in CC Switch, whereas the client-facing protocol here stays Responses.
- **HTTP 401 / 403:** check provider configuration in CC Switch; do not paste a real API key into this workbench.
- **Incomplete response:** the model may exhaust its output limit or the proxy may return an incomplete stream. Adjust a copied configuration's `limits.max_output_tokens` for CLI research; the GUI currently exposes only the model-turn limit.
- **Provider switch:** requests follow local routing, but the requested model ID must remain valid or be mapped by CC Switch.
- **Missing key in custom mode:** export the named environment variable in the terminal that launches SymmetryLab. CC Switch mode does not need this variable.

The installed CC Switch application was identified as 3.20.3 during development. The current upstream Chat-format migration guide targets 3.20.4 and later, so conversion behavior on older versions remains to be tested. Native Responses routing is the intended preset; a working local connection test is the criterion for readiness.

## References

- [CC Switch local routing documentation](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/4-proxy/4.1-service.md): default address, provider forwarding, credential management.
- [CC Switch Codex routing guide](https://github.com/farion1231/cc-switch/blob/main/docs/guides/codex-deepseek-routing-guide-en.md): client-facing Responses and upstream format conversion; version-specific applicability.
- [OpenAI Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses): request and response formats used by the adapter.
