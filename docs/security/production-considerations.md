# Production Considerations

This repository is an AWS sample/reference architecture demonstrating a
metadata-harmonization pattern. Several security controls are intentionally
absent or disabled by default so the sample stays simple to read, cheap to
run, and easy to deploy for a demo. **None of these is a bug** — each is a
deliberate scope decision for a sample repo, not for a production system.

If you are forking this repository for a real deployment, treat everything
below as required work, not optional hardening.

## Security Disclaimer

This solution is provided as a proof-of-value and is not intended as a production-ready implementation. You are responsible for evaluating how the AWS Shared Responsibility Model applies to your specific use case and for implementing the necessary security controls to meet your organization's requirements. AWS provides a broad set of security tools and configurations to support your security objectives, and it is your responsibility as the developer to ensure all aspects of your application are appropriately secured for production use.

---

## Required before production

### WAF `SizeRestrictions_BODY` override needs re-evaluation

A `wafv2.CfnWebACL` with the standard managed rule baseline
(`AWSManagedRulesCommonRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`,
`AWSManagedRulesAmazonIpReputationList`) is wired into
`infra/lib/core/index.ts`, gated behind `wafConfig.enable` in `config.yaml`
(`lib/schema.ts`) and on by default. One of those managed rules,
`SizeRestrictions_BODY`, is overridden to count-only (not block)
specifically to let this sample's 50MB CSV uploads through.

**To fix:** re-evaluate that override against your actual upload limits —
count-only means oversized-body requests are logged, not blocked. Set
`wafConfig.enable: false` only if you have a specific reason to disable the
WebACL entirely (e.g. cost during early dev).

### Amazon Bedrock Guardrails

No `guardrail` configuration exists anywhere in this repo. All of the
following require creating a Guardrail resource and passing its ID to the
`converse` calls in `schema_alignment.py` and `llm_resolution.py`:

- **Content filters for harmful categories** — not configured.
- **Content filters for prompt attacks** — not configured. Prompts are built
  from user-supplied CSV column names and values, so prompt injection is a
  residual risk beyond the application-layer XML fencing already in place
  (`utils/prompt_utils.py`'s `sanitize()`/`fence()` helpers). A Guardrail
  prompt-attack filter is the stronger, intended control.
- **Denied topics** — not configured. This is a business-policy control tied
  to a specific deployment's use case and audience; a generic sample has no
  fixed policy to encode. Define your own list based on your actual users and
  data.
- **Profanity filter** — not configured.
- **PII filters** — not configured. This is the one item most likely to be
  required in any real deployment even if the others are judged unnecessary:
  uploaded CSVs may contain PII, and it is currently sent to Bedrock
  unfiltered. Do not skip this on the reasoning that "the others are also
  off" — PII exposure risk does not scale down with sample/demo status the
  way UX-oriented filters (profanity, denied topics) do.
- **Alerting on Guardrail interventions** — not possible until a Guardrail
  exists. Once one is added, Guardrail intervention metrics are tracked by
  default in CloudWatch; wire a CloudWatch Alarm or Dashboard to them so
  interventions are visible, not silent.

### Bedrock model-invocation logging

No Bedrock invocation logging is configured. Token usage is tracked only in
application state (`models/state.py`'s `NodeTokenUsage` — `llm_calls`,
`llm_input_tokens`, `llm_output_tokens`, `embedding_calls`,
`embedding_tokens`), which is in-process and never persisted or exported.
Real call sites: `nodes/llm_resolution.py` (Strands `BedrockModel`,
`amazon.nova-pro-v1:0`), `nodes/schema_alignment.py` (direct
`bedrock-runtime.converse()`, same model), `nodes/semantic_prediction.py`
(`bedrock-runtime.invoke_model()` for embeddings,
`amazon.titan-embed-text-v2:0`), and the agent project's Strands `Agent`
(`us.anthropic.claude-sonnet-4-20250514-v1:0`).

This one is different in kind from the others on this list: it cannot be
added to this stack's CDK at all, by design, not just by omission.
`PutModelInvocationLoggingConfiguration` is an **account+region-level**
Bedrock setting — it governs logging for all Bedrock traffic in that
account/region, not just this application, so enabling it from a per-app
stack would silently change behavior for every other Bedrock consumer
sharing the account/region. There is also no native CDK support for it at
any version — confirmed by enumerating every `Cfn*` class in `aws-bedrock`,
`aws-bedrockmantle`, and `aws-bedrockagentcore`; no `CfnLoggingConfig`
exists, because CloudFormation has no resource type for this feature at all.
The only way to manage it from CDK would be an `AwsCustomResource` mutating
account-wide state from a per-app stack, with no native construct to
graduate to later.

**To add, once, at the account level — not from this repo's CDK:**

1. Enable Bedrock model-invocation logging via the AWS Console
   (Bedrock → Settings) or `aws bedrock put-model-invocation-logging-configuration`,
   directing logs to CloudWatch Logs and/or S3.
2. Add IAM for it: `bedrock:PutModelInvocationLoggingConfiguration` /
   `GetModelInvocationLoggingConfiguration` are not in
   `infra/lib/core/iam/ecs.json` today — that file only grants runtime
   `bedrock:InvokeModel*` (see the Bedrock wildcard item above).
3. Wire alerts using the pattern already established in this repo:
   `createCloudWatchAlarmAndSnsHook` (`infra/lib/shared-resources.ts`) builds
   a `logs.MetricFilter` + `sns.Topic` + `cloudwatch.Alarm` from any
   CloudWatch Log Group and an `AlarmConfig`-shaped block — point a new
   instance of it at whichever log group the account-level config above
   delivers to.
4. Invocation logs capture full prompts and completions. Confirm they need
   the same treatment as row-level CSV data below (row-level data only ever
   at DEBUG, never WARNING/ERROR) — LLM prompts can carry the same CSV
   content.

### CloudTrail data-plane logging for DynamoDB

No CDK-managed CloudTrail trail exists in this stack (verified — no
`aws-cdk-lib/aws-cloudtrail` import anywhere). The three DynamoDB tables
(`Feedback`, `MetadataSchemas`, `MetadataUploadJob`) rely solely on the
account's default Event History: ~90 days, management/control-plane events
only. There is no `GetItem`/`PutItem`/`Query`/`Scan` visibility on any table.

**To add:** a `cloudtrail.Trail` construct with an event selector whose
`dataResources` include the three table ARNs. This also matters for
auditability of any per-tenant access control you add — cross-tenant job
access on `MetadataUploadJob` was fixed in application code (an ownership
check in `metadata_validation_handler.py`), but there is still no
data-plane audit trail of who read or wrote a given record before or after
that fix.

### TLS between CloudFront and the origin

Viewer→CloudFront is HTTPS (`REDIRECT_TO_HTTPS`) and S3 enforces SSL.
CloudFront→ALB previously ran over a public network path
(`internetFacing: true`, plain `LoadBalancerV2Origin`); this has been fixed —
the ALB is now private (`internetFacing: false`, `PRIVATE_WITH_EGRESS`
subnets) and CloudFront reaches it via
`VpcOrigin.withApplicationLoadBalancer()`, so the hop now runs over a
CloudFront-managed private connection with no public network path to the ALB
at all, rather than over the AWS backbone via a publicly resolvable DNS name.

**Data in transit on this hop is still unencrypted** (`OriginProtocolPolicy.HTTP_ONLY`) —
it never crosses the open internet, but it is not TLS either. Fixing this
requires a real domain and an ACM certificate (the ALB's
`*.elb.amazonaws.com` name cannot get one issued). Before production, acquire
a domain, add an HTTPS listener on the ALB, and switch the origin protocol
policy to HTTPS-only.

### Cognito hardening

`selfSignUpEnabled: false` and `preventUserExistenceErrors: true` are already
set correctly, but there is no MFA and no `advancedSecurityMode`, and both
`adminUserPassword` and `userPassword` auth flows are enabled. For
production, add MFA and advanced security mode, and drop the `userPassword`
flow unless you specifically need it.

### Rate limiting and background-work bounds

`background_tasks.add_task(...)` has no queue and no concurrency cap, there
is no CSV row-count cap, and there is no WAF rate-based rule or budget/billing
alarm. A real deployment should add a bounded queue, a row cap on uploads, a
WAF rate rule, and a budget alarm.

### Row-level data logged above DEBUG

Several call sites log actual uploaded cell/row values at WARNING or ERROR,
which a production `logLevel: WARNING` does not suppress:

- `nodes/validation.py:253` — a per-column "Sample errors" block including
  `current_value` (truncated to 50 chars), logged via `logger.warning(...)`.
- `logging/job_status_logger.py:204,206` — a "Sample Errors" summary built
  from real `current_value`s, logged at WARNING or ERROR depending on job
  outcome.
- `nodes/semantic_prediction.py:314` — `invalid_value` interpolated directly
  into a `logger.error(...)` message.
- `api/main.py`'s exception handlers use raw `print()` (6 call sites) instead
  of the configured logger, which bypasses `LOG_LEVEL` filtering entirely —
  an unhandled exception carrying cell content in its message would print
  unconditionally regardless of configured level.

**To fix:** move the value-bearing payload out of each WARNING/ERROR call
into a separate `logger.debug(...)` call (the operational message can stay
at its current level; the data should not), and replace the `print()` calls
with the configured logger.

### Bedrock IAM permissions are wildcarded

`infra/lib/core/iam/ecs.json:24` grants `bedrock:InvokeModel` /
`InvokeModelWithResponseStream` on `arn:...:foundation-model/*` — every
foundation model in the region, not just the ones this application actually
calls (`amazon.nova-pro-v1:0`, `amazon.titan-embed-text-v2:0`, and the
agent's `us.anthropic.claude-sonnet-4-*` cross-region inference profile).

**To fix:** narrow the resource to the specific model ARNs invoked. Note the
inference profile adds real complexity here — it needs both an
`inference-profile/us.anthropic.claude-sonnet-4-*` ARN and the underlying
`foundation-model/anthropic.claude-sonnet-4-*` ARN in each region the
profile can route to, not just a single foundation-model ARN.

### Dev-stage ALB ingress is VPC-wide

`infra/lib/core/index.ts:164-171` adds an ALB security-group ingress rule
allowing inbound HTTP from the entire VPC CIDR, gated by
`deploymentStage === "dev"`. Fine for a disposable dev stack; do not carry
this pattern forward if dev config gets reused for a prod-like stage.

**To fix:** drop the rule, or scope it to a bastion/developer CIDR instead
of the whole VPC.

### Read-only root filesystem disabled

`infra/lib/api/index.ts:86` sets `readonlyRootFilesystem: false` on the
REST API container.

**To fix:** set it to `true` after verifying the container's actual write
paths (temp files, caches) still work under a read-only root.

### CloudWatch log retention and data-protection policy

Both log groups in this stack (`core/index.ts:104-110` for VPC flow logs,
`shared-resources.ts:96-104` for the ECS container logs) explicitly set
`retention: RetentionDays.INFINITE` for any non-dev deployment stage — logs
never expire in a prod-like deployment. No `DataProtectionPolicy` is
configured on either log group, so credential-shaped strings are not masked
even if a future code path were to log one.

**To fix:** set a real retention period for non-dev stages, and add a
`logs.DataProtectionPolicy` to mask sensitive data patterns.

### MCP server (`/agent` mount) authentication

`app.mount("/agent", mcp_app)` (`api/main.py`) passes no auth at all, unlike
the REST router, which gates itself behind `OIDCHTTPBearer` via
`dependencies=[Depends(OIDCHTTPBearer())] if enable_auth else []`
(`api/router.py`). Anyone who can reach the ALB can call MCP tools with zero
credentials. Not internet-reachable today — CloudFront only forwards
`/api/*` — but reachable from inside the VPC and directly via the ALB in
`dev`; treat the CloudFront path restriction as defense in depth, not the
control.

Compounding it: the one MCP tool that creates data, `submit_metadata_validation`
(`mcp/tools/validation.py`), never looks at who is calling — it generates a
job with no owner at all. The job-creation call chain
(`mcp/tools/validation.py` → `MetadataWorker.process_validation_job` →
`WorkerService.process_metadata_validation` →
`MetadataHarmonizationProcessor.process` → `DataSaver.create_job`) hardcodes
`user_id="system"` at the bottom layer, four calls removed from the MCP tool,
regardless of who actually invoked it. The IDOR fix on `MetadataUploadJob`
(an ownership check in `metadata_validation_handler.py` — see below) has
nothing meaningful to compare against for MCP-created jobs as a result.

**Not a quick patch — assessed and deliberately deferred, not just noted.**
Unlike REST, `app.mount()` has no `dependencies=` mechanism (that's an
`APIRouter`-only feature); the fix requires new ASGI middleware whose
ordering relative to the existing `process_request` middleware (which
defaults `request.state.user_id` to `"local-test-user"`) must be verified
empirically, not assumed. The ownership fix requires threading a `user_id`
parameter through four call layers down to `DataSaver.create_job`, replacing
the hardcoded `"system"` literal. Both are mechanical once designed, but
neither is a one-line change, and the identity plumbing needs to be tested
against mocked OIDC/JWKS, which is heavier than the REST-side IDOR fix.

**Before production:**
1. Add ASGI middleware (registered so it runs before `process_request`'s
   local-dev fallback) that invokes `OIDCHTTPBearer` against requests to
   `/agent/*` when `enable_auth` is on, mirroring REST's check and setting
   `request.state.user_id` the same way.
2. Inside `submit_metadata_validation`, read the caller's identity via
   `fastmcp.server.dependencies.get_http_request().state.user_id` and pass it
   through as `user_id` at each of the four call layers down to
   `DataSaver.create_job`, replacing `"system"`. Default each new parameter
   to `"system"` so existing call sites (including the REST upload path,
   which never needs to pass one) keep compiling unchanged.
3. Once any MCP tool exists that reads or mutates an *existing* job (none do
   today — `schema.py`'s four tools are read-only schema lookups), apply the
   same ownership check pattern already used on the REST side (a
   `_get_owned_job(job_id, request)`-style check in
   `metadata_validation_handler.py`).

### `brace-expansion` CVE bundled inside `aws-cdk-lib`

`aws-cdk-lib` bundles its own `minimatch`, which in turn depends on a
vulnerable `brace-expansion` (`5.0.8` as of `aws-cdk-lib@2.264.0`;
CVE-2026-69152 affects `4.0.0`–`5.0.8`). npm `overrides` in
`projects/infra/package.json` cannot reach it — `bundleDependencies` ship as
literal files inside the parent tarball, bypassing override resolution
entirely. Low real-world risk (CDK-synth-time only, no untrusted input
reaches it), but currently unfixable.

**To fix:** check whether a newer `aws-cdk-lib` release bundles a
`minimatch` whose own `brace-expansion` dependency is `>=5.0.9`. Until then
this stays accepted-as-unfixable — detail in `projects/infra/package.json`'s
`//overrides` comment.
