### The Problem This Project Solves
Cisco provides Operational Insights (OI) through Network Consulting Engineers (NCE) or a customer portal, but this requires an onboarding process and an active subscription. This works well for existing customers, but what if you don’t want to go through all the formalities just to access important information like End of Life (EOL) dates, Common Vulnerabilities and Exposures (CVE), or best practices?

This data is already available on Cisco's website, but it's scattered all over the place. You can still manually search for device product IDs or software versions to find the information, but what if we could automate that process? This project aims to make your life easier by collecting and serving this data in a more organized and automated way.

### Consider This Scenario
You buy second-hand Cisco devices or inherit a network without active support contracts. You still need to generate reports, check for EOL dates, and evaluate vulnerabilities or features. While you can manually register each device and dig through Cisco's support website, it's a slow and tedious process.

### The Solution
This project offers a standalone REST API that provides support data for Cisco devices, even if they don’t have a support contract. With this API, you should be able to:

- Quickly check EOL dates, CVEs, features, recommendations, and config best practices for any Cisco device.
- Automate data updates through microservices without manual effort.
- Serve the data via a RESTful API that can be consumed by any other application or/and tool.
- Integrate Cisco device data into your analytics and reporting tools.
- Assess the impact of updates, like understanding how upgrading a device to the latest IOS version will affect security.
- Easily extend this tool to fetch data from other vendors (like F5, Palo Alto, Arista, etc.).

### Why an Open API Matters
This solution could help potential new Cisco customers. 

By making support data accessible, it shows the value Cisco offers, potentially encouraging investment in new devices or support contracts. 

However, the purpose here isn't marketing — it’s about helping people find useful, well organised data or build their own tools on top of this one.

### No Reinventing the Wheel — Just Fetching, Organizing, and Serving Data
It’s important to understand that this project isn’t about stealing proprietary information. All the data being fetched is already publicly available on Cisco's website. This project just automates the process, providing the same information in a more efficient way.

The tools themselves don't violate Cisco’s policies, but how you use them might. So, make sure you're following Cisco's Terms of Service.

#### Note: This repository does not contain any scraped Cisco data — only tools that can gather it... :) 