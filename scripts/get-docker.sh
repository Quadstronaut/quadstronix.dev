#!/bin/bash

# Print the header (without IMAGE)
printf "%-15s %-30s %-20s %-15s\n" "ID" "STATUS" "NAMES" "POLICY"
echo "------------------------------------------------------------------------------------------------"

# Loop through container IDs to build the unified table
sudo docker ps -a --format "{{.ID}}" | while read -r id; do
    # Fetch Status and Name (separated by a pipe for safe splitting)
    info=$(sudo docker ps -a --filter "id=$id" --format "{{.ID}}|{{.Status}}|{{.Names}}")
    
    # Fetch Restart Policy via inspect
    policy=$(sudo docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$id")
    
    # Split the info and print the final aligned row
    IFS='|' read -r cid cstat cname <<< "$info"
    printf "%-15s %-30s %-20s %-15s\n" "$cid" "$cstat" "$cname" "$policy"
done
