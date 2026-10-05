# Teardown

The DataSync agent, the File Gateway and the SFTP endpoint bill by the hour, so teardown happened the same day. Nothing has deletion protection and there's no `Deny` statement anywhere, so every delete works for the account administrator.

Run from the repo folder after `source ./env.sh`.

## A: the managed services, then the instances

```bash
for p in acme umoya; do aws transfer delete-user --server-id "$SFTP_ID" --user-name partner-$p; done
aws transfer delete-server --server-id "$SFTP_ID"
aws datasync delete-task --task-arn "$TASK_ARN"
aws datasync delete-location --location-arn "$SRC_LOC"
aws datasync delete-location --location-arn "$DST_LOC"
aws datasync delete-agent --agent-arn "$AGENT_ARN"
aws storagegateway delete-file-share --file-share-arn "$SHARE_ARN" --force-delete --query FileShareARN --output text
sleep 30
aws storagegateway delete-gateway --gateway-arn "$GW_ARN" --query GatewayARN --output text
aws ec2 terminate-instances --instance-ids "$NAS_ID" "$OFFICE_ID" "$AGENT_ID" "$GW_ID" --query 'TerminatingInstances[].CurrentState.Name' --output text
```

- `--force-delete` doesn't wait for the gateway to finish uploading; everything was already in S3.
- Deleting the agent and the gateway in AWS doesn't stop their EC2 instances. `terminate-instances` does, and the gateway's 150 GiB cache disk goes with it.

Result: the share and gateway ARNs, then `shutting-down` ×4 ([`32`](screenshots/32-step12-teardown-services-and-instances.png)).

## B: bucket, logs, IAM

```bash
aws ec2 wait instance-terminated --instance-ids "$NAS_ID" "$OFFICE_ID" "$AGENT_ID" "$GW_ID"
aws s3 rm "s3://$BUCKET" --recursive --only-show-errors
aws s3api delete-bucket --bucket "$BUCKET"
aws logs delete-log-group --log-group-name "/aws/transfer/$SFTP_ID"
aws iam delete-role-policy --role-name hybrid-datasync-s3-role --policy-name migration-prefix
aws iam delete-role --role-name hybrid-datasync-s3-role
aws iam delete-role-policy --role-name hybrid-gateway-s3-role --policy-name gateway-prefix
aws iam delete-role --role-name hybrid-gateway-s3-role
aws iam delete-role-policy --role-name hybrid-sftp-partner-role --policy-name partners-prefix
aws iam delete-role --role-name hybrid-sftp-partner-role
aws iam detach-role-policy --role-name hybrid-sftp-logging-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSTransferLoggingAccess
aws iam delete-role --role-name hybrid-sftp-logging-role
aws iam remove-role-from-instance-profile --instance-profile-name hybrid-office-profile --role-name hybrid-office-role
aws iam delete-instance-profile --instance-profile-name hybrid-office-profile
aws iam detach-role-policy --role-name hybrid-office-role --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role-policy --role-name hybrid-office-role --policy-name read-gateway-share
aws iam delete-role --role-name hybrid-office-role
```

## C: network

No group refers back to a group that refers to it, so the groups delete in plain order: NAS (refers to the agent), gateway and agent (refer to the office), then office.

```bash
for g in "$NAS_SG" "$GW_SG" "$AGENT_SG" "$OFFICE_SG"; do aws ec2 delete-security-group --group-id "$g" --query Return --output text; done
aws ec2 delete-subnet --subnet-id "$SUB_ID"
aws ec2 delete-route-table --route-table-id "$RT_ID"
aws ec2 detach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
aws ec2 delete-internet-gateway --internet-gateway-id "$IGW_ID"
aws ec2 delete-vpc --vpc-id "$VPC_ID"
```

A `DependencyViolation` here means a network interface is still being released: wait a minute and run that line again.

## Clean check

```bash
aws transfer list-servers --query 'Servers[].ServerId' --output text
aws datasync list-agents --query 'Agents[].AgentArn' --output text
aws datasync list-tasks --query 'Tasks[].TaskArn' --output text
aws storagegateway list-gateways --query 'Gateways[].GatewayARN' --output text
aws ec2 describe-instances --filters Name=tag:Name,Values=kgotla-nas,kgotla-office,kgotla-datasync-agent,kgotla-file-gateway Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].InstanceId' --output text
aws ec2 describe-vpcs --filters Name=tag:Name,Values=kgotla-dc-vpc --query 'Vpcs[].VpcId' --output text
aws s3api list-buckets --query 'Buckets[?starts_with(Name,`kgotla-hybrid`)].Name' --output text
aws iam list-roles --query 'Roles[?starts_with(RoleName,`hybrid-`)].RoleName' --output text
aws datasync list-locations --query 'Locations[].LocationArn' --output text
```

Every line printed nothing ([`33`](screenshots/33-step12-clean-check.png)). The VPC, bucket and role checks being empty confirms blocks B and C completed.

The SSH key pairs for the two partners stay in `~/.ssh` on my machine; they open nothing now that the server is gone, and can be deleted.
