---
title: Migrate from AWS Network Load Balancer to Azure Load Balancer
description: Step-by-step guide to migrate your AWS NLB to Azure Load Balancer with detailed configuration mappings and best practices.
author: azure-migration-team
ms.author: azuremigration
ms.date: 06/06/2025
ms.service: azure-migrate
ms.subservice: aws-migration
ms.topic: how-to
ms.custom: aws-migration, load-balancing, network-load-balancer
---

# Migrate from AWS Network Load Balancer to Azure Load Balancer

This guide provides detailed steps to migrate your AWS Network Load Balancer (NLB) to Azure Load Balancer. Azure Load Balancer offers equivalent layer 4 load balancing capabilities with additional features like HA Ports and outbound rules.

## Overview

Azure Load Balancer is a high-performance, ultra-low latency layer 4 (TCP/UDP) load balancer. Like AWS NLB, it handles millions of requests per second while maintaining extremely low latency, making it ideal for performance-sensitive applications.

### Key benefits of Azure Load Balancer

- **Ultra-low latency**: Sub-millisecond latency addition
- **High performance**: Millions of flows per second
- **Zone redundancy**: Built-in high availability across zones
- **Static IP support**: Dedicated public IP addresses
- **HA Ports**: Load balance across all ports simultaneously
- **Outbound rules**: Granular control over outbound connectivity
- **Cross-zone load balancing**: Included at no extra cost

### Migration complexity: Low

Typical migration time: 1-2 weeks for standard deployments

## Prerequisites

Before starting the migration:

- Azure subscription with appropriate permissions (Network Contributor role)
- Access to AWS NLB configuration and AWS console
- List of backend instances and their IP addresses
- Understanding of your application's network requirements
- Azure CLI installed or access to Azure Cloud Shell
- Network connectivity planned between Azure and backends (if hybrid)

### Required permissions

Ensure you have these Azure RBAC roles:
- Network Contributor on the resource group
- Virtual Machine Contributor (if creating VMs)
- Reader access to Log Analytics workspace

## Pre-migration assessment

Document your current NLB configuration thoroughly.

### Document NLB configuration

Export your NLB configuration:

```bash
# Export NLB configuration
aws elbv2 describe-load-balancers --names my-nlb-name --type network > nlb-config.json

# Export target groups
aws elbv2 describe-target-groups --load-balancer-arn <nlb-arn> > nlb-target-groups.json

# Export listeners
aws elbv2 describe-listeners --load-balancer-arn <nlb-arn> > nlb-listeners.json

# Export target health
for tg in $(aws elbv2 describe-target-groups --load-balancer-arn <nlb-arn> --query 'TargetGroups[*].TargetGroupArn' --output text); do
    aws elbv2 describe-target-health --target-group-arn $tg > health-$tg.json
done
```

### Identify static IP requirements

Document static IP configurations:

```bash
# List Elastic IPs associated with NLB
aws ec2 describe-addresses --filters "Name=association.resource-type,Values=network-load-balancer" > elastic-ips.json

# Document subnet mappings
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <nlb-arn> > nlb-attributes.json
```

### Map health check configurations

Create a mapping table for health checks:

| NLB Setting | Azure LB Setting | Notes |
|-------------|------------------|-------|
| Protocol | protocol | TCP/HTTP/HTTPS |
| Port | port | Same port mapping |
| Interval | intervalInSeconds | Minimum 5 seconds |
| Threshold | numberOfProbes | Unhealthy threshold |
| Timeout | - | Not configurable in Azure |

### Review performance requirements

Document current performance metrics:

```bash
# Get CloudWatch metrics for baseline
aws cloudwatch get-metric-statistics \
    --namespace AWS/NetworkELB \
    --metric-name ActiveFlowCount_TCP \
    --dimensions Name=LoadBalancer,Value=<nlb-name> \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Maximum
```

## Step 1: Prepare Azure environment

Set up the networking foundation for Azure Load Balancer.

### Create resource group

```bash
# Set variables
RG_NAME="rg-loadbalancer-migration"
LOCATION="eastus2"
LB_NAME="lb-production"

# Create resource group
az group create \
    --name $RG_NAME \
    --location $LOCATION
```

### Configure virtual network

Create VNet with proper subnet design:

```bash
# Create virtual network
az network vnet create \
    --resource-group $RG_NAME \
    --name vnet-production \
    --address-prefix 10.0.0.0/16 \
    --location $LOCATION

# Create backend subnet
az network vnet subnet create \
    --resource-group $RG_NAME \
    --vnet-name vnet-production \
    --name subnet-backend \
    --address-prefix 10.0.1.0/24

# Create bastion subnet (optional, for management)
az network vnet subnet create \
    --resource-group $RG_NAME \
    --vnet-name vnet-production \
    --name AzureBastionSubnet \
    --address-prefix 10.0.254.0/24
```

### Plan IP addressing

Reserve IP addresses for the load balancer:

```bash
# Create multiple public IPs for different services (if needed)
az network public-ip create \
    --resource-group $RG_NAME \
    --name pip-lb-frontend-01 \
    --sku Standard \
    --allocation-method Static \
    --zone 1 2 3

# Create additional IPs if migrating multiple NLB listeners
az network public-ip create \
    --resource-group $RG_NAME \
    --name pip-lb-frontend-02 \
    --sku Standard \
    --allocation-method Static \
    --zone 1 2 3
```

### Set up network security groups

Configure NSGs for backend subnet:

```bash
# Create NSG for backend subnet
az network nsg create \
    --resource-group $RG_NAME \
    --name nsg-backend

# Allow health probe traffic from Azure Load Balancer
az network nsg rule create \
    --resource-group $RG_NAME \
    --nsg-name nsg-backend \
    --name Allow-AzureLoadBalancer \
    --priority 100 \
    --direction Inbound \
    --source-address-prefixes AzureLoadBalancer \
    --destination-address-prefixes '*' \
    --destination-port-ranges '*' \
    --protocol '*' \
    --access Allow

# Allow application traffic (example: TCP 443)
az network nsg rule create \
    --resource-group $RG_NAME \
    --nsg-name nsg-backend \
    --name Allow-HTTPS \
    --priority 200 \
    --direction Inbound \
    --source-address-prefixes Internet \
    --destination-address-prefixes '*' \
    --destination-port-ranges 443 \
    --protocol Tcp \
    --access Allow

# Associate NSG with subnet
az network vnet subnet update \
    --resource-group $RG_NAME \
    --vnet-name vnet-production \
    --name subnet-backend \
    --network-security-group nsg-backend
```

## Step 2: Create Azure Load Balancer

Deploy Load Balancer with Standard SKU for production workloads.

### Choose Standard SKU

Always use Standard SKU for production:

| Feature | Basic SKU | Standard SKU |
|---------|-----------|--------------|
| Backend pool size | 300 instances | 1000 instances |
| Health probes | Basic | HTTP/HTTPS/TCP |
| Availability Zones | No | Yes |
| HA Ports | No | Yes |
| Outbound rules | No | Yes |
| SLA | No | 99.99% |

### Create Load Balancer

```bash
# Create Load Balancer
az network lb create \
    --resource-group $RG_NAME \
    --name $LB_NAME \
    --sku Standard \
    --public-ip-address pip-lb-frontend-01 \
    --frontend-ip-name frontend-01 \
    --backend-pool-name backend-pool-01 \
    --location $LOCATION
```

### Configure frontend IP configuration

Add additional frontend IPs if needed:

```bash
# Add second frontend IP (if migrating multiple NLB listeners)
az network lb frontend-ip create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name frontend-02 \
    --public-ip-address pip-lb-frontend-02
```

### Configure availability zones

Standard Load Balancer is zone-redundant by default:

```bash
# Verify zone configuration
az network lb show \
    --resource-group $RG_NAME \
    --name $LB_NAME \
    --query "frontendIpConfigurations[0].zones"
```

## Step 3: Configure backend pools

Set up backend pools to match NLB target groups.

### Add virtual machines

If backends are Azure VMs:

```bash
# Get VM NIC IDs
VM_NIC_ID1=$(az vm show \
    --resource-group $RG_NAME \
    --name vm-backend-01 \
    --query "networkProfile.networkInterfaces[0].id" -o tsv)

# Add VM to backend pool
az network nic ip-config address-pool add \
    --resource-group $RG_NAME \
    --nic-name $(basename $VM_NIC_ID1) \
    --ip-config-name ipconfig1 \
    --lb-name $LB_NAME \
    --address-pool backend-pool-01
```

### Configure NIC-based pools

For traditional VM-based backends:

```bash
# Create additional backend pools
az network lb address-pool create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name backend-pool-databases \
    --backend-address-name database-01 \
    --vnet vnet-production
```

### Set up IP-based pools

For non-Azure or hybrid backends:

```bash
# Create IP-based backend pool
az network lb address-pool create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name backend-pool-external

# Add IP addresses
az network lb address-pool address add \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --pool-name backend-pool-external \
    --name external-server-01 \
    --ip-address 192.168.1.10

az network lb address-pool address add \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --pool-name backend-pool-external \
    --name external-server-02 \
    --ip-address 192.168.1.11
```

### Configure session persistence

Set up session affinity if required:

```bash
# Session persistence is configured per rule (see next section)
# Options: None, SourceIP, SourceIPProtocol
```

## Step 4: Create load balancing rules

Map NLB listeners to Azure Load Balancer rules.

### Map NLB listeners to LB rules

Create rules for each NLB listener:

```bash
# Create load balancing rule for HTTPS traffic
az network lb rule create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name rule-https \
    --protocol Tcp \
    --frontend-port 443 \
    --backend-port 443 \
    --frontend-ip-name frontend-01 \
    --backend-pool-name backend-pool-01 \
    --probe-name probe-https \
    --idle-timeout 4 \
    --enable-tcp-reset true \
    --load-distribution Default
```

### Configure protocol settings

Map protocol-specific settings:

```bash
# Create UDP load balancing rule (if needed)
az network lb rule create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name rule-udp-dns \
    --protocol Udp \
    --frontend-port 53 \
    --backend-port 53 \
    --frontend-ip-name frontend-01 \
    --backend-pool-name backend-pool-01 \
    --probe-name probe-dns \
    --idle-timeout 4 \
    --load-distribution SourceIPProtocol
```

### Set idle timeout values

Configure appropriate idle timeouts:

| Application Type | Recommended Timeout | Notes |
|-----------------|---------------------|-------|
| Web applications | 4-30 minutes | Based on session length |
| Database connections | 30 minutes | Long-running queries |
| Real-time apps | 4 minutes | Minimum value |
| IoT devices | 30 minutes | Persistent connections |

### Enable TCP reset if needed

TCP reset helps applications handle connection failures gracefully:

```bash
# Update rule to enable TCP reset
az network lb rule update \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name rule-https \
    --enable-tcp-reset true
```

## Step 5: Configure health probes

Create health probes matching NLB health checks.

### Map NLB health checks

Create equivalent health probes:

```bash
# Create HTTPS health probe
az network lb probe create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name probe-https \
    --protocol Https \
    --port 443 \
    --path /health \
    --interval 5 \
    --probe-threshold 2

# Create TCP health probe
az network lb probe create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name probe-tcp-database \
    --protocol Tcp \
    --port 3306 \
    --interval 15 \
    --probe-threshold 3
```

### Configure probe protocols

Choose appropriate probe protocol:

| Protocol | Use Case | Configuration |
|----------|----------|---------------|
| TCP | Port availability | Simple port check |
| HTTP | Application health | Custom path check |
| HTTPS | Secure endpoints | Certificate validation |

### Set threshold values

Configure probe thresholds:

```bash
# Conservative settings for critical services
az network lb probe update \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name probe-https \
    --interval 5 \
    --probe-threshold 3  # Failures before unhealthy

# Aggressive settings for fast failover
az network lb probe update \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name probe-tcp-database \
    --interval 5 \
    --probe-threshold 2
```

### Test probe functionality

Verify probes are working:

```bash
# Check backend health status
az network lb show \
    --resource-group $RG_NAME \
    --name $LB_NAME \
    --query "backendAddressPools[0].backendIPConfigurations[*].id"
```

## Step 6: Testing and validation

Thoroughly test the load balancer configuration.

### Connectivity testing

Test basic connectivity:

```bash
# Get Load Balancer public IP
LB_IP=$(az network public-ip show \
    --resource-group $RG_NAME \
    --name pip-lb-frontend-01 \
    --query ipAddress -o tsv)

# Test TCP connectivity
nc -zv $LB_IP 443

# Test with curl (for HTTP/HTTPS)
curl -v https://$LB_IP/health

# Test from multiple source IPs
for i in {1..10}; do
    curl -s -o /dev/null -w "%{http_code} - %{remote_ip}\n" https://$LB_IP/
done
```

### Performance validation

Run performance tests:

```bash
# Install performance testing tools
sudo apt-get install -y iperf3 apache2-utils

# TCP throughput test
iperf3 -c $LB_IP -p 5001 -t 60

# HTTP load test
ab -n 10000 -c 100 -k https://$LB_IP/

# Sustained load test
while true; do
    curl -s https://$LB_IP/ > /dev/null
    sleep 0.1
done &
```

### Failover testing

Test high availability:

```bash
# Stop backend VM to test failover
az vm stop \
    --resource-group $RG_NAME \
    --name vm-backend-01

# Monitor traffic distribution
watch -n 1 'curl -s https://$LB_IP/server-info'

# Restart VM
az vm start \
    --resource-group $RG_NAME \
    --name vm-backend-01
```

### Load distribution verification

Verify even distribution:

```bash
# Script to test load distribution
#!/bin/bash
declare -A servers
for i in {1..1000}; do
    response=$(curl -s https://$LB_IP/server-id)
    ((servers[$response]++))
done

echo "Load distribution:"
for server in "${!servers[@]}"; do
    echo "$server: ${servers[$server]} requests"
done
```

## Step 7: Migration cutover

Execute the production migration with minimal downtime.

### Update DNS records

Prepare DNS updates:

```bash
# Get current NLB DNS
aws elbv2 describe-load-balancers \
    --names my-nlb-name \
    --query 'LoadBalancers[0].DNSName' \
    --output text

# Get Azure Load Balancer IP
az network public-ip show \
    --resource-group $RG_NAME \
    --name pip-lb-frontend-01 \
    --query ipAddress -o tsv

# Update DNS records (example with Azure DNS)
az network dns record-set a update \
    --resource-group rg-dns \
    --zone-name example.com \
    --name www \
    --set aRecords[0].ipv4Address=$LB_IP
```

### Monitor traffic flow

Set up monitoring for cutover:

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
    --resource-group $RG_NAME \
    --workspace-name law-loadbalancer

# Enable Load Balancer metrics
az monitor diagnostic-settings create \
    --resource $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --name lb-diagnostics \
    --workspace $(az monitor log-analytics workspace show -g $RG_NAME -n law-loadbalancer --query id -o tsv) \
    --metrics '[{"enabled": true, "category": "AllMetrics"}]'

# Create alert for high failure rate
az monitor metrics alert create \
    --resource-group $RG_NAME \
    --name alert-probe-failures \
    --scopes $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --condition "avg DipAvailability < 95" \
    --window-size 5m \
    --evaluation-frequency 1m
```

### Validate functionality

Post-cutover validation:

```bash
# Continuous monitoring script
#!/bin/bash
while true; do
    echo "$(date): Testing Load Balancer..."
    
    # Test connectivity
    if curl -s -f https://$LB_IP/health > /dev/null; then
        echo "Health check: PASS"
    else
        echo "Health check: FAIL"
    fi
    
    # Check response times
    response_time=$(curl -o /dev/null -s -w '%{time_total}' https://$LB_IP/)
    echo "Response time: ${response_time}s"
    
    sleep 10
done
```

### Document configuration

Create migration documentation:

```bash
# Export Load Balancer configuration
az network lb show \
    --resource-group $RG_NAME \
    --name $LB_NAME \
    --output json > azure-lb-config.json

# Export all rules
az network lb rule list \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --output table > lb-rules.txt

# Export health probes
az network lb probe list \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --output table > lb-probes.txt
```

## Post-migration tasks

Optimize and secure your Load Balancer deployment.

### Enable diagnostics

Configure comprehensive logging:

```bash
# Enable all diagnostic logs
az monitor diagnostic-settings create \
    --resource $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --name lb-all-diagnostics \
    --storage-account $(az storage account show -g $RG_NAME -n stlbdiagnostics --query id -o tsv) \
    --logs '[{"category": "LoadBalancerAlertEvent", "enabled": true},
             {"category": "LoadBalancerProbeHealthStatus", "enabled": true}]'
```

### Configure alerts

Set up proactive monitoring:

```bash
# Alert for backend pool health
az monitor metrics alert create \
    --resource-group $RG_NAME \
    --name alert-backend-health \
    --scopes $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --condition "avg VipAvailability < 99" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --action-group ag-lb-admins

# Alert for data path availability
az monitor metrics alert create \
    --resource-group $RG_NAME \
    --name alert-data-path \
    --scopes $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --condition "avg DatapathAvailability < 99" \
    --window-size 5m \
    --evaluation-frequency 1m
```

### Optimize performance

Fine-tune for optimal performance:

```bash
# Enable accelerated networking on backend VMs
az network nic update \
    --resource-group $RG_NAME \
    --name nic-backend-01 \
    --accelerated-networking true

# Configure optimal MTU size
az network nic update \
    --resource-group $RG_NAME \
    --name nic-backend-01 \
    --network-security-group nsg-backend
```

### Review security settings

Enhance security posture:

```bash
# Review and tighten NSG rules
az network nsg rule list \
    --resource-group $RG_NAME \
    --nsg-name nsg-backend \
    --output table

# Enable DDoS protection (if not already enabled)
az network ddos-protection create \
    --resource-group $RG_NAME \
    --name ddos-protection-plan \
    --location $LOCATION

# Associate with VNet
az network vnet update \
    --resource-group $RG_NAME \
    --name vnet-production \
    --ddos-protection-plan ddos-protection-plan
```

## Troubleshooting common issues

### Asymmetric routing

If experiencing connection issues:

1. Ensure return traffic uses same path
2. Configure source NAT if needed:

```bash
# Create outbound rule for SNAT
az network lb outbound-rule create \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name outbound-rule-snat \
    --frontend-ip-configs frontend-01 \
    --protocol All \
    --idle-timeout 15 \
    --outbound-ports 10000 \
    --address-pool backend-pool-01
```

### Health probe failures

Troubleshoot probe issues:

```bash
# Check probe configuration
az network lb probe show \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name probe-https

# Test probe endpoint directly
curl -v https://backend-vm-ip:443/health

# Check NSG rules
az network nsg rule list \
    --resource-group $RG_NAME \
    --nsg-name nsg-backend \
    --query "[?destinationAddressPrefix=='*' && access=='Allow']"
```

### Connection drops

For unexpected disconnections:

1. Check idle timeout settings
2. Enable TCP keepalive on applications
3. Review TCP reset configuration

```bash
# Increase idle timeout
az network lb rule update \
    --resource-group $RG_NAME \
    --lb-name $LB_NAME \
    --name rule-https \
    --idle-timeout 30
```

### Performance degradation

Address performance issues:

```bash
# Check Load Balancer metrics
az monitor metrics list \
    --resource $(az network lb show -g $RG_NAME -n $LB_NAME --query id -o tsv) \
    --metric "ByteCount" "PacketCount" "SYNCount" \
    --interval PT1M \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)

# Verify backend VM performance
az vm list-usage \
    --location $LOCATION \
    --output table
```

## Next steps

- Configure [outbound connectivity](https://docs.microsoft.com/azure/load-balancer/outbound-rules) for backend pools
- Implement [cross-region load balancing](https://docs.microsoft.com/azure/load-balancer/cross-region-overview)
- Review [security best practices](https://docs.microsoft.com/azure/load-balancer/security-recommendations)
- Explore [HA Ports configuration](https://docs.microsoft.com/azure/load-balancer/load-balancer-ha-ports-overview) for NVA scenarios

For additional resources:
- [Load Balancer documentation](https://docs.microsoft.com/azure/load-balancer/)
- [Load Balancer FAQ](https://docs.microsoft.com/azure/load-balancer/load-balancer-faq)
- [Azure networking limits](https://docs.microsoft.com/azure/azure-resource-manager/management/azure-subscription-service-limits#networking-limits)