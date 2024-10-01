
# Cisco EOL-EOS-FN-CVE Support - Open Data Alternative

Cisco traditionally provides customers with network Operational Insights (OI) through Network Consulting Engineers (NCE) or via a customer portal. While this is great for existing customers to use the Cisco API's, it requires an onboarding process and active subscription. 

### The Problem this solution attempt to solve
But what if you could access Cisco insights and data without the formalities? Why should critical yet public network information like EOL dates, CVEs, or best practices be locked behind an onboarding process or service contract? They are available on Cisco's website anyway, the problem is that cisco is so big and old that all the insights are literaly all over the place. Ofcourse we can still find all we need manually searhing by device product id or software versions but what if we can automate that process, serve it and make our life easier?

Consider this scenario:
- You purchase Cisco devices second-hand or inherit a network without existing support contracts. 
- You still want to generate reports, check for EOL dates, or evaluate potential vulnerabilities and features of these devices.
- While it is possible, the manual process of registering each device and fetching data from Cisco's support website is time-consuming.

### The Alternative
This solution provides a **standalone REST API** designed to serve suppporting data, even for devices not covered under a support contract. With this API, you can:

- Quickly check EOL dates, CVEs, features, recommendations and best practices for any Cisco device.
- Automate dataset updates trough microservices without the need for manual intervention.
- Serve the data trough Restfull API ready to be consumed by any API.
- Integrate Cisco device data into your analytics and reporting tools.
- Evaluate the impact of updates, such as understanding how upgrading an N9K switch to the latest IOS version affects your network security.
- You can easely create and plug you own tools to fetch support data from other vendors (F5, Palo Alto, Arista etc)
  
### Why an Open API Matters
This alternative solution organise the access to Cisco data, eliminating the need for onboarding while providing a fast, efficient, and scalable way to manage your Cisco infrastructure.

Moreover, this would encourage potential new customers to buy Cisco devices after seeing the quality of support and data available to them. Once they see the value Cisco offers, they may decide to invest in new devices and opt for support contracts. Without this, they may never know what Cisco can provide or what to expect, missing out on valuable opportunities. I am not doing it for the sake of marketing or anything like this, just to help people find an idea, use or build their own tools on top of this one.
 
### No Reinventing the Wheel – Simply Fetching, Normalizing and Serving the Data
It's important to note that I am not reinventing the wheel or stealing proprietary information. I am simply collecting what already exists on Cisco's publicly available website. This allows me to create a cold-data dataset that can be freely served, making the same information accessible in a more automated and efficient way.

The tools on their own are not against the Cisco's policy but their improper usage maybe, so you must to make sure all you do complies with Cisco's TOS: https://www.cisco.com/c/en/us/about/legal/terms-conditions.html

The repo does not contain any scraped Cisco's data only tools that can obtain it :)
