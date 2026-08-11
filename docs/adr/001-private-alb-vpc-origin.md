# 001. Private ALB behind a CloudFront VPC origin

## Context

The application load balancer (`Core.alb`, `projects/infra/lib/core/index.ts`) was
`internetFacing: true` in public subnets, and CloudFront reached it through a plain
`origins.LoadBalancerV2Origin`, i.e. a public DNS name. The only thing standing
between the open internet and the ALB was a security group rule scoped to
CloudFront's managed prefix list (`com.amazonaws.global.cloudfront.origin-facing`).

This was an unnecessary public attack surface: the ALB never needs to be
reachable from outside CloudFront, so making it internet-facing at all is
exposure with no corresponding benefit. CloudFront VPC origins were the
known fix, but treated as untested — until a sibling project on this host
(`HS-One`, `packages/infra/src/infra/stacks/services_stack.py`) turned up as
a working precedent already running this exact pattern in production CDK,
which is what triggered doing it here rather than leaving it as a documented
possibility.

## Decision

Move the ALB into private subnets (`internetFacing: false`,
`vpcSubnets: { subnetType: PRIVATE_WITH_EGRESS }`) and have CloudFront reach it via
`origins.VpcOrigin.withApplicationLoadBalancer()` instead of
`origins.LoadBalancerV2Origin`. CloudFront now connects over a service-managed ENI
in the VPC rather than the ALB's public DNS name, so there is no public network path
to the ALB at all.

Also replaced the `custom.AwsCustomResource` / `describeManagedPrefixLists` Lambda
that looked up the CloudFront prefix list ID with the native
`ec2.PrefixList.fromLookup()` construct — same lookup, no custom resource, no IAM
policy statement, no Lambda. This wasn't required by the VPC-origin change, but the
custom resource existed only to feed that same ingress rule, so replacing both
together avoided leaving one half of a simplification undone.

No changes to `shared-resources.ts` or `api/index.ts`: the Fargate service and its
target group already lived in the same private subnets, so nothing downstream of
the ALB needed to move.

## Consequences

- **Closes exposure, not encryption.** The listener is still `port: 80` /
  `ApplicationProtocol.HTTP`, and the VPC origin still uses
  `OriginProtocolPolicy.HTTP_ONLY`. Traffic between CloudFront and the ALB is
  unencrypted either way; what changed is that it now transits a private,
  CloudFront-managed connection instead of the public internet-facing DNS name.
  HS-One's stack, the precedent for this change, has the same limitation for the
  same reason (see below).
- **Encryption is still blocked on a domain.** ACM cannot issue a certificate for
  the ALB's own `*.elb.amazonaws.com` name (an AWS-owned domain cannot be
  domain-validated), and this project has no custom domain provisioned. Until that
  changes, HTTPS on this hop isn't reachable regardless of ALB placement — see
  [Production Considerations](../security/production-considerations.md) for the
  remaining steps.
- **New/changed infra:** an `AWS::CloudFront::VpcOrigin` resource and its
  service-managed ENI (created lazily by CloudFront after deploy), replacing the
  `AwsCustomResource` prefix-list-lookup Lambda that no longer exists.
- Verified via `cdk synth` against the real dev config with live AWS
  credentials, not just unit-test dummy values: the synthesized template shows
  `Scheme: internal` on the ALB, an `AWS::CloudFront::VpcOrigin` with
  `OriginProtocolPolicy: http-only`, the distribution's `/api/*` origin pointing at
  it via `VpcOriginConfig`/`Fn::GetAtt`, and the security group ingress rule sourced
  from the real resolved prefix list ID (`pl-3b927c52`) rather than `0.0.0.0/0`.
  `cdk deploy` was not run — this ADR records the design decision, not a completed
  deployment.
