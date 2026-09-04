# Providers | OpenCode

> Source: https://opencode.ai/docs/providers
> Cached: 2026-09-03T16:35:20.115Z

---

# Providers

Using any LLM provider in OpenCode.

       OpenCode uses the [AI SDK](https://ai-sdk.dev/) and [Models.dev](https://models.dev) to support **75+ LLM providers** and it supports running local models.

To add a provider you need to:

- Add the API keys for the provider using the `/connect` command.

- Configure the provider in your OpenCode config.

### [Credentials](#credentials)

When you add a provider’s API keys with the `/connect` command, they are stored
in `~/.local/share/opencode/auth.json`.

### [Config](#config)

You can customize the providers through the `provider` section in your OpenCode
config.

#### [Base URL](#base-url)

You can customize the base URL for any provider by setting the `baseURL` option. This is useful when using proxy services or custom endpoints.

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "anthropic": {      "options": {        "baseURL": "https://api.anthropic.com/v1"      }    }  }}
```

#### [Hiding models](#hiding-models)

You can hide specific models from the `/models` picker for a provider using the `blacklist` option. This is useful when a provider exposes models you don’t want to use or select.

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "anthropic": {      "blacklist": ["claude-opus-4-20250514"]    }  }}
```

The inverse `whitelist` option hides every model except the ones listed.

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "anthropic": {      "whitelist": ["claude-sonnet-4-20250514"]    }  }}
```

Both options take an array of model IDs — the same IDs shown in the `/models` picker.

- `blacklist` removes the listed models from the picker.

- `whitelist` keeps only the listed models and hides the rest.

- You can combine them: `whitelist` narrows the set, then `blacklist` removes entries from it.

## [OpenCode Zen](#opencode-zen)

OpenCode Zen is a list of models provided by the OpenCode team that have been
tested and verified to work well with OpenCode. [Learn more](/docs/zen).
Tip

If you are new, we recommend starting with OpenCode Zen.

Run the `/connect` command in the TUI, select `OpenCode Zen`, and head to [opencode.ai/auth](https://opencode.ai/zen).

```
/connect
```

Sign in, add your billing details, and copy your API key.

Paste your API key.

```
┌ API key││└ enter
```

Run `/models` in the TUI to see the list of models we recommend.

```
/models
```

It works like any other provider in OpenCode and is completely optional to use.

## [OpenCode Go](#opencode-go)

OpenCode Go is a low cost subscription plan that provides reliable access to popular open coding models provided by the OpenCode team that have been
tested and verified to work well with OpenCode.

Run the `/connect` command in the TUI, select `OpenCode Go`, and head to [opencode.ai/auth](https://opencode.ai/zen).

```
/connect
```

Sign in, add your billing details, and copy your API key.

Paste your API key.

```
┌ API key││└ enter
```

Run `/models` in the TUI to see the list of models we recommend.

```
/models
```

It works like any other provider in OpenCode and is completely optional to use.

## [Directory](#directory)

Let’s look at some of the providers in detail. If you’d like to add a provider to the
list, feel free to open a PR.
Note

Don’t see a provider here? Submit a PR.

### [302.AI](#302ai)

Head over to the [302.AI console](https://302.ai/), create an account, and generate an API key.

Run the `/connect` command and search for **302.AI**.

```
/connect
```

Enter your 302.AI API key.

```
┌ API key││└ enter
```

Run the `/models` command to select a model.

```
/models
```

### [Amazon Bedrock](#amazon-bedrock)

To use Amazon Bedrock with OpenCode:

Head over to the **Model catalog** in the Amazon Bedrock console and request
access to the models you want.
Tip

You need to have access to the model you want in Amazon Bedrock.

**Configure authentication** using one of the following methods:

#### [Environment Variables (Quick Start)](#environment-variables-quick-start)

Set one of these environment variables while running opencode:

Terminal window```
# Option 1: Using AWS access keysAWS_ACCESS_KEY_ID=XXX AWS_SECRET_ACCESS_KEY=YYY opencode
# Option 2: Using named AWS profileAWS_PROFILE=my-profile opencode
# Option 3: Using Bedrock bearer tokenAWS_BEARER_TOKEN_BEDROCK=XXX opencode
```

Or add them to your bash profile:

~/.bash_profile```
export AWS_PROFILE=my-dev-profileexport AWS_REGION=us-east-1
```

#### [Configuration File (Recommended)](#configuration-file-recommended)

For project-specific or persistent configuration, use `opencode.json`:

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "amazon-bedrock": {      "options": {        "region": "us-east-1",        "profile": "my-aws-profile"      }    }  }}
```

**Available options:**

- `region` - AWS region (e.g., `us-east-1`, `eu-west-1`)

- `profile` - AWS named profile from `~/.aws/credentials`

- `endpoint` - Custom endpoint URL for VPC endpoints (alias for generic `baseURL` option)

Tip

Configuration file options take precedence over environment variables.

#### [Advanced: VPC Endpoints](#advanced-vpc-endpoints)

If you’re using VPC endpoints for Bedrock:

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "amazon-bedrock": {      "options": {        "region": "us-east-1",        "profile": "production",        "endpoint": "https://bedrock-runtime.us-east-1.vpce-xxxxx.amazonaws.com"      }    }  }}
```

Note

The `endpoint` option is an alias for the generic `baseURL` option, using AWS-specific terminology. If both `endpoint` and `baseURL` are specified, `endpoint` takes precedence.

#### [Authentication Methods](#authentication-methods)

- **`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`**: Create an IAM user and generate access keys in the AWS Console

- **`AWS_PROFILE`**: Use named profiles from `~/.aws/credentials`. First configure with `aws configure --profile my-profile` or `aws sso login`

- **`AWS_BEARER_TOKEN_BEDROCK`**: Generate long-term API keys from the Amazon Bedrock console

- **`AWS_WEB_IDENTITY_TOKEN_FILE` / `AWS_ROLE_ARN`**: For EKS IRSA (IAM Roles for Service Accounts) or other Kubernetes environments with OIDC federation. These environment variables are automatically injected by Kubernetes when using service account annotations.

#### [Authentication Precedence](#authentication-precedence)

Amazon Bedrock uses the following authentication priority:

- **Bearer Token** - `AWS_BEARER_TOKEN_BEDROCK` environment variable or token from `/connect` command

- **AWS Credential Chain** - Profile, access keys, shared credentials, IAM roles, Web Identity Tokens (EKS IRSA), instance metadata

Note

When a bearer token is set (via `/connect` or `AWS_BEARER_TOKEN_BEDROCK`), it takes precedence over all AWS credential methods including configured profiles.

Run the `/models` command to select the model you want.

```
/models
```

Note

For custom inference profiles, use the model and provider name in the key and set the `id` property to the arn. This ensures correct caching.

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "amazon-bedrock": {      // ...      "models": {        "anthropic-claude-sonnet-4.5": {          "id": "arn:aws:bedrock:us-east-1:xxx:application-inference-profile/yyy"        }      }    }  }}
```

### [Anthropic](#anthropic)

Once you’ve signed up, run the `/connect` command and select Anthropic.

```
/connect
```

Here you can select the **Claude Pro/Max** option and it’ll open your browser
and ask you to authenticate.
```
┌ Select auth method││ Manually enter API Key└
```

Now all the Anthropic models should be available when you use the `/models` command.

```
/models
```

There are plugins that allow you to use your Claude Pro/Max models with
OpenCode. Anthropic explicitly prohibits this.Previous versions of OpenCode came bundled with these plugins but that is no
longer the case as of 1.3.0Other companies support freedom of choice with developer tooling - you can use
the following subscriptions in OpenCode with zero setup:

- ChatGPT Plus

- Github Copilot

- Gitlab Duo

### [Atomic Chat](#atomic-chat)

You can configure opencode to use local models through [Atomic Chat](https://atomic.chat), a desktop application that runs local LLMs behind an OpenAI-compatible API server (default endpoint `http://127.0.0.1:1337/v1`).

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "atomic-chat": {      "npm": "@ai-sdk/openai-compatible",      "name": "Atomic Chat (local)",      "options": {        "baseURL": "http://127.0.0.1:1337/v1"      },      "models": {        "&#x3C;your-model-id>": {          "name": "&#x3C;your-model-name>"        }      }    }  }}
```

&#x22;: {          &#x22;name&#x22;: &#x22;&#x22;        }      }    }  }}">
In this example:

- `atomic-chat` is the custom provider ID. This can be any string you want.

- `npm` specifies the package to use for this provider. Here, `@ai-sdk/openai-compatible` is used for any OpenAI-compatible API.

- `name` is the display name for the provider in the UI.

- `options.baseURL` is the endpoint for the local server. Change the host and port to match your Atomic Chat setup.

- `models` is a map of model IDs to their display names. Each ID must match the `id` returned by `GET /v1/models` — run `curl http://127.0.0.1:1337/v1/models` to list the ids currently loaded in Atomic Chat.

Tip

If tool calls aren’t working well, pick a loaded model with strong tool-calling support (for example, a Qwen-Coder or DeepSeek-Coder variant).

### [Azure OpenAI](#azure-openai)

Note

If you encounter “I’m sorry, but I cannot assist with that request” errors, try changing the content filter from **DefaultV2** to **Default** in your Azure resource.

Head over to the [Azure portal](https://portal.azure.com/) and create an **Azure OpenAI** resource. You’ll need:

- **Resource name**: This becomes part of your API endpoint (`https://RESOURCE_NAME.openai.azure.com/`)

- **API key**: Either `KEY 1` or `KEY 2` from your resource

Go to [Azure AI Foundry](https://ai.azure.com/) and deploy a model.

Note

The deployment name must match the model name for opencode to work properly.

Run the `/connect` command and search for **Azure**.

```
/connect
```

Enter your API key.

```
┌ API key││└ enter
```

Set your resource name as an environment variable:

Terminal window```
AZURE_RESOURCE_NAME=XXX opencode
```

Or add it to your bash profile:

~/.bash_profile```
export AZURE_RESOURCE_NAME=XXX
```

Run the `/models` command to select your deployed model.

```
/models
```

#### [Microsoft Entra ID (Azure CLI)](#microsoft-entra-id-azure-cli)

You can use your Azure CLI session instead of an API key. [Install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli), run `az login`, then run `/connect`, select **Azure**, and choose **Microsoft Entra ID (Azure CLI)**. Enter the Azure Resource name when prompted. Use `az login --tenant TENANT_ID` if the Resource belongs to a different tenant.

Find the Resource name by opening your Azure OpenAI or Foundry Resource in the [Azure portal](https://portal.azure.com/) or [Microsoft Foundry](https://ai.azure.com/). It is also the first part of the endpoint: `my-models` in `https://my-models.openai.azure.com/` or `https://my-models.services.ai.azure.com/`. If your identity can list Resources, you can also find their names and Resource groups with:

Terminal window```
az cognitiveservices account list \  --query "[].{name:name,resourceGroup:resourceGroup}" \  --output table
```

OpenCode does not query Azure management APIs or discover deployments. Select a model whose catalog name matches your deployment, or configure its deployment name explicitly:

opencode.json```
{  "$schema": "https://opencode.ai/config.json",  "provider": {    "azure": {      "models": {        "gpt-5-mini": {          "id": "gpt-production"        }      }    }  }}
```

Assign your identity the inference role required by the deployment: **Cognitive Services OpenAI User** for Azure OpenAI models or **Cognitive Services User** for other Foundry models. OpenCode refreshes access tokens through the Azure CLI, including versions earlier than 2.54.0, so you only need to sign in again when the CLI session expires.

### [Azure Cognitive Services](#azure-cognitive-services)

Head over to the [Azure portal](https://portal.azure.com/) and create an **Azure OpenAI** resource. You’ll need:

- **Resource name**: This becomes part of your API endpoint (`https://AZURE_COGNITIVE_SERVICES_RESOURCE_NAME.cognitiveservices.azure.com/`)

- **API key**: Either `KEY 1` or `KEY 2` from your resource

Go to [Azure AI Foundry](https://ai.azure.com/) and deploy a model.

Note

The deployment name must match the model name for opencode to work properly.

Run the `/connect` command and search for **Azure Cognitive Services**.

```
/connect
```

Enter your API key.

```
┌ API key││└ enter
```

Set your resource name as an environment variable:

Terminal window```
AZURE_COGNITIVE_SERVICES_RESOURCE_NAME=XXX opencode
```

Or add it to your bash profile:

~/.bash_profile```
export AZURE_COGNITIVE_SERVICES_RESOURCE_NAME=XXX
```

Run the `/models` command to select your deployed model.

```
/models
```

### [Baseten](#baseten)

Head over to the [Baseten](https://app.baseten.co/), create an account, and generate an API key.

Run the `/connect` command and search for **Baseten**.

```
/connect
```

Enter your Baseten API key.

```
┌ API key││└ enter
```

Run the `/models` command to select a model.

```
/models
```

### [Cerebras](#cerebras)

Head over to the [Cerebras console](https://inference.cerebras.ai/), create an account, and generate an API key.

Run the `/connect` command and search for **Cerebras**.

```
/connect
```

Enter your Cerebras API key.

```
┌ API key││└ enter
```

Run the `/models` command to select a model like *Qwen 3 Coder 480B*.

```
/models
```

### [Cloudflare AI Gateway](#cloudflare-ai-gateway)

Cloudflare AI Gateway lets you access models from OpenAI, Anthropic, Workers AI, and more through a unified endpoint. With [Unified Billing](https://developers.cloudflare.com/ai-gateway/features/unified-billing/) you don’t need separate API keys for each provider.

Head over to the [Cloudflare dashboard](https://dash.cloudflare.com/), navigate to **AI** > **AI Gateway**, and create a new gateway. Note your **Account ID** and **Gateway ID**.

Run the `/connect` command and search for **Cloudflare AI Gateway**.

```
/connect
```

Enter your **Account ID** when prompted.

```
┌ Enter your Cloudflare Account ID││└ enter
```

Enter your **Gateway ID** when prompted.

```
┌ Enter your Cloudflare AI Gateway ID││└ enter
```

Enter your **Cloudflare API token**.

```
┌ Gateway API token││└ enter
```

Run the

... [Content truncated]