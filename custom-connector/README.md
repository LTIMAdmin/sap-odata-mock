# LTIM SAP Delta API Custom Connector

Import `apiDefinition.swagger.json` as a custom connector inside `LTM Operations Solution`.

## Solution environment variables

Create these Text environment variables:

| Display name | Schema name | Development value |
|---|---|---|
| SAP Delta API Host | `ltm_SAPDeltaApiHost` | `sap-odata-mock.onrender.com` |
| SAP Delta API Base URL | `ltm_SAPDeltaApiBaseUrl` | `/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV` |

The OpenAPI definition is already configured with these values on the connector General tab:

- Host: `@environmentVariables("ltm_SAPDeltaApiHost")`
- Base URL: `@environmentVariables("ltm_SAPDeltaApiBaseUrl")`

Create the connector with both `apiDefinition.swagger.json` and `apiProperties.json`. Power Platform resolves the environment variables when the custom connector is saved. If a value changes later, resave the custom connector so it picks up the new value.

## Authentication

Use Basic authentication for the temporary Render API. Enter credentials when creating the connector connection. Add the resulting connection reference to `LTM Operations Solution`.

Do not store the password in a Text environment variable. If the production connector later needs a client secret, use a Secret environment variable backed by Azure Key Vault.

## Operation

`GetDeltaEvents` exposes:

- `$top`
- `$skip`
- `$filter`
- `$orderby`
- `$select`
- `$format`

Flow 1 must invoke `GetDeltaEvents` through this connector. It must not use a direct HTTP action for the SAP API.
