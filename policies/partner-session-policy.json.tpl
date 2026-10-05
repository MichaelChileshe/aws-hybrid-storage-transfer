{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOwnFolderOnly",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::@@BUCKET@@",
      "Condition": { "StringLike": { "s3:prefix": ["partners/${transfer:UserName}/*", "partners/${transfer:UserName}"] } }
    },
    {
      "Sid": "ReadWriteOwnFolderOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::@@BUCKET@@/partners/${transfer:UserName}/*"
    }
  ]
}
