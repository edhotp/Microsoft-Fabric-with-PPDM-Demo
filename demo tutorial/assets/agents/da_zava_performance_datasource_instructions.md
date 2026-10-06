# Data source instructions - sm_zava_performance (agent da_zava_performance)

Paste the text below the line into **Data source instructions** of the `sm_zava_performance` source in the data agent `da_zava_performance`.
The data agent passes these instructions to the DAX query generator. Agent instructions alone are not enough: in workshop testing, without these instructions the generator tried to filter on `PublicationId` and returned empty results.

---

This semantic model contains exactly one approved SSOT publication.
- Never filter on any PublicationId column, on the 'publication' table, or on the [Trust Banner] measure. Never use TREATAS on PublicationId.
- Use the existing measures: [Gross BOE], [Net WI BOE], [Target BOE], [Target Achievement %], [Data Completeness %], [Lost BOE Gross], [Lost BOE Net WI], [Loss Value USD Gross], [Affected Wells], [Downtime Hours], [Opex USD], [Current Publication], [Approved By].
- Countries: filter 'dim_asset'[CountryName] ("Algeria", "Malaysia", "Iraq"). Fields: 'dim_asset'[AssetName]. Wells: 'dim_well'[WellId].
- Incidents: filter 'dim_incident'[IncidentId], for example:
  EVALUATE CALCULATETABLE(ROW("Lost BOE Gross", [Lost BOE Gross], "Lost BOE Net WI", [Lost BOE Net WI]), 'dim_incident'[IncidentId] = "INC-MY-001")
- Source line: EVALUATE ROW("Current Publication", [Current Publication], "Approved By", [Approved By]) without any filter.
