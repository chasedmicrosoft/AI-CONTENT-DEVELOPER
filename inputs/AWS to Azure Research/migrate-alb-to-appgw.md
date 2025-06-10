---
title: Migrate from AWS Application Load Balancer to Azure Application Gateway
description: Step-by-step guide to migrate your AWS ALB to Azure Application Gateway with detailed configuration mappings and best practices.
author: azure-migration-team
ms.author: azuremigration
ms.date: 06/06/2025
ms.service: azure-migrate
ms.subservice: aws-migration
ms.topic: how-to
ms.custom: aws-migration, load-balancing, application-gateway
---

# Migrate from AWS Application Load Balancer to Azure Application Gateway

This guide provides detailed steps to migrate your AWS Application Load Balancer (ALB) to Azure Application Gateway. Follow these instructions to ensure a smooth migration with minimal downtime.

## Overview

Azure Application Gateway is a layer 7 load balancer that provides application delivery controller (ADC) capabilities, similar to AWS ALB. It offers additional features like integrated Web Application Firewall (WAF), static VIP addresses, and advanced URL rewriting capabilities.

### Key benefits of Application Gateway

- **Integrated WAF**: Built-in web application firewall at no additional cost
- **Static VIP**: Predictable IP addresses for firewall rules
- **Autoscaling**: Automatic scaling based on load
- **Zone redundancy**: Built-in high availability across availability zones
- **SSL offload**: Centralized SSL certificate management
- **Advanced routing**: URL path-based and multi-site routing

### Migration complexity: Medium

Typical migration time: 2-4 weeks for a standard web application

## Prerequisites

Before starting the migration:

- Azure subscription with appropriate permissions (Contributor role on resource group)
- Access to AWS ALB configuration and AWS console
- Current SSL certificates exported from AWS Certificate Manager
- Azure CLI installed locally or access to Azure Cloud Shell
- Understanding of your application's routing requirements
- Network connectivity between Azure and your backend servers (if hybrid)

### Required tools

```bash
# Install Azure CLI (if not using Cloud Shell)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install AWS CLI for configuration export
pip install awscli

# Install jq for JSON parsing
sudo apt-get install jq
```

## Pre-migration assessment

Proper assessment ensures a smooth migration process.

### Document current ALB configuration

Export your ALB configuration for reference:

```bash
# Export ALB configuration
aws elbv2 describe-load-balancers --names my-alb-name > alb-config.json

# Export target groups
aws elbv2 describe-target-groups > target-groups.json

# Export listeners
aws elbv2 describe-listeners --load-balancer-arn <alb-arn> > listeners.json

# Export rules
for listener in $(aws elbv2 describe-listeners --load-balancer-arn <alb-arn> --query 'Listeners[*].ListenerArn' --output text); do
    aws elbv2 describe-rules --listener-arn $listener > rules-$listener.json
done
```

### Identify dependencies

Document all dependencies:

- Backend server IP addresses or FQDNs
- Security group rules and network ACLs
- Auto Scaling group associations
- CloudWatch alarms and metrics
- WAF rules (if using AWS WAF)
- Route 53 DNS records

### Map features to Application Gateway

| AWS ALB Feature | Application Gateway Equivalent | Notes |
|-----------------|-------------------------------|-------|
| Target Groups | Backend Pools | Similar concept |
| Listeners | Listeners | Multi-site capable |
| Rules | Request Routing Rules | Path and host-based |
| Health Checks | Health Probes | HTTP/HTTPS probes |
| Sticky Sessions | Cookie-based Affinity | Application Gateway managed |
| Access Logs | Diagnostic Logs | Azure Monitor integration |
| WAF | Integrated WAF_v2 SKU | Built-in, no extra cost |
| Auto Scaling | Autoscaling (v2 SKU) | Automatic |

### Plan for differences

Key differences to address:

1. **Static IP**: Application Gateway provides static VIP (ALB uses dynamic IPs)
2. **Health probe thresholds**: Azure uses different default values
3. **SSL policies**: Different naming but equivalent functionality
4. **Routing capabilities**: ALB has more granular routing options
5. **Monitoring**: CloudWatch to Azure Monitor transition

## Step 1: Prepare Azure environment

Set up the foundation for your Application Gateway.

### Create resource group

```bash
# Set variables
RG_NAME="rg-appgateway-migration"
LOCATION="eastus2"

# Create resource group
az group create --name $RG_NAME --location $LOCATION
```

### Set up virtual network

Application Gateway requires a dedicated subnet:

```bash
# Create virtual network
az network vnet create \
    --resource-group $RG_NAME \
    --name vnet-appgateway \
    --address-prefix 10.0.0.0/16 \
    --subnet-name subnet-appgateway \
    --subnet-prefix 10.0.1.0/24

# Create backend subnet (if backends are in Azure)
az network vnet subnet create \
    --resource-group $RG_NAME \
    --vnet-name vnet-appgateway \
    --name subnet-backend \
    --address-prefix 10.0.2.0/24
```

### Configure network security groups

Create NSG for Application Gateway subnet:

```bash
# Create NSG
az network nsg create \
    --resource-group $RG_NAME \
    --name nsg-appgateway

# Allow Application Gateway management traffic
az network nsg rule create \
    --resource-group $RG_NAME \
    --nsg-name nsg-appgateway \
    --name Allow-GatewayManager \
    --priority 100 \
    --direction Inbound \
    --source-address-prefixes GatewayManager \
    --destination-address-prefixes '*' \
    --destination-port-ranges 65200-65535 \
    --protocol Tcp \
    --access Allow

# Allow HTTP/HTTPS traffic
az network nsg rule create \
    --resource-group $RG_NAME \
    --nsg-name nsg-appgateway \
    --name Allow-Web \
    --priority 200 \
    --direction Inbound \
    --source-address-prefixes Internet \
    --destination-address-prefixes '*' \
    --destination-port-ranges 80 443 \
    --protocol Tcp \
    --access Allow

# Associate NSG with subnet
az network vnet subnet update \
    --resource-group $RG_NAME \
    --vnet-name vnet-appgateway \
    --name subnet-appgateway \
    --network-security-group nsg-appgateway
```

### Prepare SSL certificates

Export certificates from AWS and prepare for Azure:

```bash
# Create Key Vault for certificate storage
az keyvault create \
    --resource-group $RG_NAME \
    --name kv-appgw-certs \
    --location $LOCATION

# Convert PEM to PFX (if needed)
openssl pkcs12 -export -out certificate.pfx -inkey private.key -in certificate.crt

# Upload certificate to Key Vault
az keyvault certificate import \
    --vault-name kv-appgw-certs \
    --name my-ssl-cert \
    --file certificate.pfx \
    --password 'your-pfx-password'
```

## Step 2: Create Application Gateway

Deploy Application Gateway with appropriate configuration.

### Choose appropriate SKU

For production workloads, use Standard_v2 or WAF_v2:

| SKU | Use Case | Features |
|-----|----------|----------|
| Standard_v2 | General web apps | Autoscaling, Zone redundancy |
| WAF_v2 | Security-focused | All Standard_v2 + WAF |

### Deploy Application Gateway

Create Application Gateway with basic configuration:

```bash
# Create public IP
az network public-ip create \
    --resource-group $RG_NAME \
    --name pip-appgateway \
    --allocation-method Static \
    --sku Standard \
    --zone 1 2 3

# Create WAF policy (if using WAF_v2)
az network application-gateway waf-policy create \
    --resource-group $RG_NAME \
    --name waf-policy-default

# Create Application Gateway
az network application-gateway create \
    --resource-group $RG_NAME \
    --name appgw-production \
    --location $LOCATION \
    --sku WAF_v2 \
    --capacity 2 \
    --vnet-name vnet-appgateway \
    --subnet subnet-appgateway \
    --public-ip-address pip-appgateway \
    --http-settings-cookie-based-affinity Enabled \
    --http-settings-port 80 \
    --http-settings-protocol Http \
    --frontend-port 80 \
    --routing-rule-type Basic \
    --servers 10.0.2.4 10.0.2.5 \
    --waf-policy waf-policy-default \
    --zones 1 2 3 \
    --enable-autoscale \
    --min-capacity 2 \
    --max-capacity 10
```

### Configure health probes

Create custom health probes matching ALB health checks:

```bash
# Create health probe
az network application-gateway probe create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name health-probe-http \
    --protocol Http \
    --host-name-from-http-settings true \
    --path /health \
    --interval 30 \
    --timeout 30 \
    --threshold 3

# Update backend HTTP settings to use probe
az network application-gateway http-settings update \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name appGatewayBackendHttpSettings \
    --probe health-probe-http
```

## Step 3: Migrate configurations

Map your ALB configurations to Application Gateway.

### Routing rules

#### ALB path-based routing → AG URL path maps

Create URL path-based routing:

```bash
# Create path map
az network application-gateway url-path-map create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name path-map-api \
    --paths /api/* \
    --http-settings appGatewayBackendHttpSettings \
    --address-pool appGatewayBackendPool

# Add additional paths
az network application-gateway url-path-map rule create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --path-map-name path-map-api \
    --name images-rule \
    --paths /images/* \
    --http-settings appGatewayBackendHttpSettings \
    --address-pool images-backend-pool
```

#### ALB host-based routing → AG multi-site listeners

Configure multi-site hosting:

```bash
# Create multi-site listener
az network application-gateway http-listener create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name listener-contoso \
    --frontend-port 80 \
    --frontend-ip appGatewayFrontendIP \
    --host-names www.contoso.com contoso.com

# Create routing rule for the listener
az network application-gateway rule create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name rule-contoso \
    --rule-type Basic \
    --http-listener listener-contoso \
    --http-settings appGatewayBackendHttpSettings \
    --address-pool contoso-backend-pool
```

#### ALB query string routing → AG custom rules

For complex routing based on query strings, use rewrite rules:

```bash
# Create rewrite rule set
az network application-gateway rewrite-rule set create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name rewrite-rules

# Add condition and action
az network application-gateway rewrite-rule create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --rule-set-name rewrite-rules \
    --name query-string-rule \
    --sequence 100 \
    --condition "var_query_string contains 'version=v2'" \
    --action-set "url=/v2/api"
```

### SSL/TLS configuration

Configure SSL termination and policies:

```bash
# Add SSL certificate
az network application-gateway ssl-cert create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name ssl-cert-production \
    --key-vault-secret-id $(az keyvault certificate show --vault-name kv-appgw-certs --name my-ssl-cert --query sid -o tsv)

# Create HTTPS listener
az network application-gateway http-listener create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name listener-https \
    --frontend-port 443 \
    --frontend-ip appGatewayFrontendIP \
    --ssl-cert ssl-cert-production

# Configure SSL policy
az network application-gateway ssl-policy set \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --policy-type Predefined \
    --policy-name AppGwSslPolicy20220101
```

### Health checks

Configure health probes matching ALB settings:

| ALB Setting | Application Gateway Setting | Default Value |
|-------------|----------------------------|---------------|
| Interval | interval | 30 seconds |
| Timeout | timeout | 30 seconds |
| Healthy threshold | threshold | 3 |
| Unhealthy threshold | threshold | 3 |
| Matcher | match-status-codes | 200-399 |

```bash
# Create custom probe with specific settings
az network application-gateway probe create \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name custom-health-probe \
    --protocol Https \
    --path /api/health \
    --interval 10 \
    --timeout 10 \
    --threshold 2 \
    --match-status-codes 200-202
```

## Step 4: Configure WAF (if applicable)

If using WAF_v2 SKU, configure Web Application Firewall.

### Enable WAF on Application Gateway

```bash
# Update WAF configuration
az network application-gateway waf-config set \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --enabled true \
    --firewall-mode Prevention \
    --rule-set-type OWASP \
    --rule-set-version 3.2
```

### Migrate AWS WAF rules

Map AWS WAF rules to Azure WAF custom rules:

```bash
# Create custom rule for IP blocking
az network application-gateway waf-policy custom-rule create \
    --resource-group $RG_NAME \
    --policy-name waf-policy-default \
    --name BlockIPRule \
    --priority 100 \
    --rule-type MatchRule \
    --action Block \
    --match-condition "RemoteAddr IPMatch 192.168.1.0/24 10.0.0.0/8"

# Create custom rule for geo-blocking
az network application-gateway waf-policy custom-rule create \
    --resource-group $RG_NAME \
    --policy-name waf-policy-default \
    --name GeoBlockRule \
    --priority 110 \
    --rule-type MatchRule \
    --action Block \
    --match-condition "GeoMatch CN RU"
```

### Configure custom rules

Add specific protection rules:

```bash
# Rate limiting rule
az network application-gateway waf-policy custom-rule create \
    --resource-group $RG_NAME \
    --policy-name waf-policy-default \
    --name RateLimitRule \
    --priority 120 \
    --rule-type RateLimitRule \
    --action Block \
    --rate-limit-duration OneMin \
    --rate-limit-threshold 100 \
    --match-condition "RequestUri Contains /api/login"
```

## Step 5: Testing and validation

Thoroughly test before migrating production traffic.

### Test routing rules

Validate each routing configuration:

```bash
# Test path-based routing
curl -H "Host: www.example.com" http://<appgw-ip>/api/test
curl -H "Host: www.example.com" http://<appgw-ip>/images/logo.png

# Test host-based routing
curl -H "Host: www.contoso.com" http://<appgw-ip>/
curl -H "Host: www.fabrikam.com" http://<appgw-ip>/

# Test HTTPS
curl -k https://<appgw-ip>/secure-endpoint
```

### Validate SSL termination

Check SSL configuration:

```bash
# Test SSL certificate
openssl s_client -connect <appgw-ip>:443 -servername www.example.com

# Verify SSL protocols
nmap --script ssl-enum-ciphers -p 443 <appgw-ip>
```

### Performance testing

Run load tests to validate performance:

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run performance test
ab -n 10000 -c 100 https://<appgw-ip>/

# Compare with ALB baseline
# - Requests per second
# - Time per request
# - Transfer rate
```

### Security validation

Test WAF functionality:

```bash
# Test SQL injection protection
curl "https://<appgw-ip>/search?q=1' OR '1'='1"

# Test XSS protection
curl "https://<appgw-ip>/comment?text=<script>alert('xss')</script>"

# Verify blocked requests in logs
az monitor activity-log list \
    --resource-group $RG_NAME \
    --offset 1h \
    --query "[?contains(resourceId, 'appgw-production')]"
```

## Step 6: Migration cutover

Execute the production cutover with minimal downtime.

### DNS preparation

Prepare for DNS cutover:

1. Note current ALB DNS name
2. Get Application Gateway public IP or DNS name
3. Reduce DNS TTL to 60 seconds (24 hours before cutover)

```bash
# Get Application Gateway details
az network application-gateway show \
    --resource-group $RG_NAME \
    --name appgw-production \
    --query "frontendIpConfigurations[0].publicIpAddress.id" \
    --output tsv | xargs az network public-ip show --ids \
    --query "{IP:ipAddress, DNS:dnsSettings.fqdn}"
```

### Traffic switching strategy

Choose your cutover strategy:

#### Option 1: DNS-based cutover (recommended)
```bash
# Update Route 53 or your DNS provider
# Change CNAME or A record to point to Application Gateway
# Monitor traffic shift in both ALB and Application Gateway metrics
```

#### Option 2: Weighted routing (gradual)
```bash
# Use Route 53 weighted routing
# Start with 10% to Application Gateway
# Gradually increase weight as confidence grows
```

### Monitoring during cutover

Set up real-time monitoring:

```bash
# Create dashboard for cutover monitoring
az monitor metrics list \
    --resource $APPGW_ID \
    --metric "TotalRequests" "HealthyHostCount" "ResponseStatus" \
    --interval PT1M

# Set up alerts
az monitor metrics alert create \
    --resource-group $RG_NAME \
    --name high-error-rate \
    --resource $APPGW_ID \
    --metric ResponseStatus \
    --condition "count 5xx > 10" \
    --window-size 5m
```

### Rollback procedures

Prepare rollback plan:

1. Keep ALB running during validation period
2. Document rollback DNS changes
3. Test rollback procedure in advance

```bash
# Rollback script
#!/bin/bash
# Update DNS to point back to ALB
# Alert team of rollback
# Document issues encountered
```

## Post-migration tasks

Complete these tasks after successful migration.

### Performance optimization

Fine-tune Application Gateway settings:

```bash
# Adjust autoscaling based on observed patterns
az network application-gateway update \
    --resource-group $RG_NAME \
    --name appgw-production \
    --min-capacity 3 \
    --max-capacity 20

# Enable HTTP/2 for better performance
az network application-gateway update \
    --resource-group $RG_NAME \
    --name appgw-production \
    --enable-http2 true

# Configure connection draining
az network application-gateway update \
    --resource-group $RG_NAME \
    --name appgw-production \
    --connection-draining-timeout 30
```

### Cost optimization

Implement cost-saving measures:

1. **Right-size capacity units**
   - Monitor actual usage
   - Adjust min/max capacity
   - Consider reserved capacity

2. **Optimize data transfer**
   - Enable compression
   - Implement caching rules
   - Minimize cross-region traffic

```bash
# Enable compression
az network application-gateway http-settings update \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name appGatewayBackendHttpSettings \
    --enable-compression true
```

### Monitoring setup

Configure comprehensive monitoring:

```bash
# Enable diagnostic logs
az monitor diagnostic-settings create \
    --resource $APPGW_ID \
    --name appgw-diagnostics \
    --workspace $LOG_ANALYTICS_WORKSPACE_ID \
    --logs '[{"category": "ApplicationGatewayAccessLog", "enabled": true},
             {"category": "ApplicationGatewayPerformanceLog", "enabled": true},
             {"category": "ApplicationGatewayFirewallLog", "enabled": true}]' \
    --metrics '[{"category": "AllMetrics", "enabled": true}]'

# Create custom dashboard
az portal dashboard create \
    --resource-group $RG_NAME \
    --name AppGatewayDashboard \
    --input-path dashboard-template.json
```

### Documentation update

Update your documentation:

- Network diagrams with new architecture
- Runbooks for common operations
- Troubleshooting guides
- Contact information for Azure support

## Troubleshooting common issues

### Connection timeouts

If experiencing timeouts:

1. Check NSG rules allow traffic
2. Verify backend health probe status
3. Adjust timeout settings:

```bash
az network application-gateway http-settings update \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name appGatewayBackendHttpSettings \
    --timeout 60
```

### SSL certificate errors

For SSL issues:

1. Verify certificate is properly imported
2. Check certificate chain is complete
3. Ensure SNI is configured for multi-site

```bash
# View SSL certificate details
az network application-gateway ssl-cert show \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --name ssl-cert-production
```

### Routing misconfigurations

If requests aren't routing correctly:

1. Review rule priority order
2. Check path patterns use correct syntax
3. Verify backend pool membership

```bash
# List all routing rules
az network application-gateway rule list \
    --resource-group $RG_NAME \
    --gateway-name appgw-production \
    --output table
```

### Performance issues

For performance problems:

1. Check capacity units are sufficient
2. Review backend server performance
3. Enable connection multiplexing
4. Verify autoscaling is working

```bash
# View current capacity
az network application-gateway show \
    --resource-group $RG_NAME \
    --name appgw-production \
    --query "sku.capacity"
```

## Next steps

- Review [monitoring best practices](monitor-performance.md) for Application Gateway
- Implement [advanced routing scenarios](configure-routing-rules.md)
- Explore [WAF tuning guide](implement-waf-policies.md)
- Consider [multi-region deployment](migrate-alb-nlb-to-front-door.md) with Azure Front Door

For additional support:
- [Application Gateway documentation](https://docs.microsoft.com/azure/application-gateway/)
- [Application Gateway FAQ](https://docs.microsoft.com/azure/application-gateway/application-gateway-faq)
- [Azure Support](https://azure.microsoft.com/support/options/)