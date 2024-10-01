
# Cisco Support - Open Data Alternative

Business Critical Services (BCS) traditionally provides customers with network Operational Insights (OI) through Network Consulting Engineers (NCE) or via a customer portal. While this is valuable, customers have expressed the need for a more flexible consumption model—one that integrates seamlessly into their existing workflows.

### What does the BCS OI API offer?
The BCS OI API allows customers to prioritize and automate actionable, data-driven Cisco recommendations for improving network availability, performance, risk mitigation, and other key optimization priorities. Customers can integrate these insights directly into their systems, such as ServiceNow, Splunk, and other automation workflows.

### The Problem this solution attempt to solve
While BCS 3.0 customers can access the OI API, this solution requires an onboarding process and active subscription. But what if you could access Cisco insights and data without the formalities? Why should critical network information like EOL dates, CVEs, or best practices be locked behind an onboarding process or service contract?

Consider this scenario:
- You purchase Cisco devices second-hand or inherit a network without existing support contracts. 
- You still want to generate reports, check for EOL dates, or evaluate potential vulnerabilities and features of these devices.
- While it is possible, the manual process of registering each device and fetching data from Cisco's support website is time-consuming.

### Our Open Data Alternative
This solution provides a **standalone REST API** designed to serve as an open data point for integrating Cisco insights, even for devices not covered under a support contract. With this API, you can:

- Quickly check EOL dates, CVEs, features, recommendations and best practices for any Cisco device.
- Automate dataset updates trough microservices without the need for manual intervention.
- Serve the data trough Restfull API ready to be consumed by any API
- Integrate Cisco device data into your analytics and reporting tools.
- Evaluate the impact of updates, such as understanding how upgrading an N9K switch to the latest IOS version affects your network security.

### Why an Open API Matters
I truly believe that opening up such data to the public would increase Cisco’s overall business value by streamlining second-hand device usage and simplifying operational insights for everyone. This alternative solution democratizes access to Cisco data, eliminating the need for onboarding while providing a fast, efficient, and scalable way to manage your Cisco infrastructure.

Moreover, this would encourage potential new customers to buy Cisco devices after seeing the quality of support and data available to them. Once they see the value Cisco offers, they may decide to invest in new devices and opt for support contracts. Without this, they may never know what Cisco can provide or what to expect, missing out on valuable opportunities.
 

### No Reinventing the Wheel – Simply Scraping Available Data
It's important to note that I am not reinventing the wheel or stealing proprietary information. I am simply collecting what already exists on Cisco's publicly available website. This allows us to create a cold-data dataset that can be freely served, making the same information accessible in a more automated and efficient way.
The tools on their own are not against the Cisco's policy but their improper usage maybe so you make sure all you do complies with Cisco's TOS: https://www.cisco.com/c/en/us/about/legal/terms-conditions.html
The repo does not contain Cisco's data only tools that can obtain it.