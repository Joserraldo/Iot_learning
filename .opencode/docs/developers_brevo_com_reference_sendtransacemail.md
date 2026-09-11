# Send a transactional email | Brevo API Documentation

> Source: https://developers.brevo.com/reference/sendtransacemail
> Cached: 2026-09-10T15:43:40.013Z

---

[Email API](/reference/send-transac-email)[Transactional email](/reference/send-transac-email)# Send a transactional email

Ask a question|Copy page|[View as Markdown](https://developers.brevo.com/reference/send-transac-email.md)|More actionsPOSThttps://api.brevo.com/v3/smtp/emailStatic content exampleDynamic content exampleresponsePOST/v3/smtp/emailTypeScript1import { BrevoClient } from "@getbrevo/brevo";23async function main() {4    const client = new BrevoClient({5        apiKey: "YOUR_API_KEY_HERE",6    });7    await client.transactionalEmails.sendTransacEmail({8        htmlContent: "<html><head></head><body><p>Hello,</p>This is my first transactional email sent from Brevo.</p></body></html>",9        sender: {10            email: "hello@brevo.com",11            name: "Alex from Brevo",12        },13        subject: "Hello from Brevo!",14        to: [15            {16                email: "johndoe@example.com",17                name: "John Doe",18            },19        ],20    });21}22main();Try it201Static content example1{2  "messageId": "<201798300811.5787683@relay.domain.com>"3}Send a transactional email to one or more recipients, either using inline HTML content or a pre-built template via `templateId`. You can schedule emails for future delivery using `scheduledAt` (UTC, up to 5-minute delay), send multiple personalized versions with `messageVersions` (max 2000 total recipients, 99 per version), and attach files via URL or base64-encoded content. A `sender` and `subject` are required when no `templateId` is provided; when a `templateId` is used, the template&#x27;&#x27;s sender and subject are applied unless overridden.### Authentication

api-keystringThe API key should be passed in the request headers as `api-key` for authentication.

### Request

Request body parameters for sending a transactional emailattachmentlist of objectsOptionalArray of attachment objects. Each attachment must include either an absolute URL (no local file paths) or base64-encoded content, along with the attachment filename. The `name` field is required when `content` is provided. Supported file extensions: xlsx, xls, ods, docx, docm, doc, csv, pdf, txt, gif, jpg, jpeg, png, tif, tiff, rtf, bmp, cgm, css, shtml, html, htm, zip, xml, ppt, pptx, tar, ez, ics, mobi, msg, pub, eps, odt, mp3, m4a, m4v, wma, ogg, flac, wav, aif, aifc, aiff, mp4, mov, avi, mkv, mpeg, mpg, wmv, pkpass, xlsm. When `templateId` is specified: if the template uses the New Template Language format, both `url` and `content` attachment types are supported; if the template uses the Old Template Language format, the `attachment` parameter is ignored.
Show 3 propertiesbatchIdstringOptionalUUIDv4 identifier for the scheduled batch of transactional emails. If omitted, a valid UUIDv4 batch identifier is automatically generated.bcclist of objectsOptionalArray of BCC recipient objects. Each object contains an email address and an optional name.
Show 3 propertiescclist of objectsOptionalArray of CC recipient objects. Each object contains an email address and an optional name.
Show 3 propertiesheadersmap from strings to anyOptionalCustom email headers (non-standard headers) to include in the email. The `sender.ip` header can be set to specify the IP address used for sending transactional emails (dedicated IP users only). Header names must use Title-Case-Format (words separated by hyphens with the first letter of each word capitalized). Headers not in this format are automatically converted. Standard email headers are not supported. Example: `{"sender.ip":"1.2.3.4", "X-Mailin-custom":"some_custom_value", "Idempotency-Key":"abc-123"}`
htmlContentstringOptionalHTML body content of the email. Required when `templateId` is not provided. Ignored when `templateId` is provided.

messageVersionslist of objectsOptionalArray of message version objects for sending customized email variants. The `templateId` can be customized per version only if a global `templateId` is provided. The `htmlContent` and `textContent` can be customized per version only if at least one of these is present in the global parameters. Global parameters such as `to` (required), `bcc`, `cc`, `replyTo`, and `subject` can be customized per version. Maximum total recipients per API request is 2000. Maximum recipients per message version is 99. Individual `params` objects must not exceed 100 KB. Cumulative `params` across all versions must not exceed 1000 KB. See https://developers.brevo.com/docs/batch-send-transactional-emails for detailed usage instructions.
Show 8 propertiesparamsmap from strings to anyOptionalKey-value pairs for template variable substitution. Only applicable when the template uses the New Template Language format.

replyToobjectOptionalReply-to email address (required) and optional display name. Recipients will use this address when replying to the email.

Show 2 propertiesscheduledAtdatetimeOptionalUTC date-time when the email should be sent (format: YYYY-MM-DDTHH:mm:ss.SSSZ). Include timezone information in the date-time value. Scheduled emails may be delayed by up to 5 minutes.

senderobjectOptionalSender information. Required when `templateId` is not provided. Specify either an email address (with optional name) or a sender ID. The `name` field is ignored when `id` is provided.

Show 3 propertiessubjectstringOptionalEmail subject line. Required when `templateId` is not provided.

tagslist of stringsOptionalArray of tags for categorizing and filtering emailstemplateIdlongOptionalTemplate identifiertextContentstringOptionalPlain text body content of the email. Ignored when `templateId` is provided.

tolist of objectsOptionalArray of recipient objects. Each object contains an email address and an optional display name. Required when `messageVersions` is not provided. Ignored when `messageVersions` is provided. Example: `[{"name":"Jimmy", "email":"jimmy@example.com"}, {"name":"Joe", "email":"joe@example.com"}]`
Show 3 properties### Response

201Transactional email sent successfullymessageIdstringOptionalMessage ID of the transactional email sentmessageIdslist of stringsOptional### Errors

400Bad Request Error