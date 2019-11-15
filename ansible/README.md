
Copy all ansible files to the ansible bucket

```shell script
$ aws s3 sync . s3://<ANSIBLE_CODE_BUCKET> --delete --exclude README.md
```
