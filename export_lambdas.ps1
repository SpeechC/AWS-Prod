Param(
  [string]$Region   = "us-east-1",
  [string]$RepoUrl  = "https://github.com/SpeechC/AWS-Prod.git",  # <-- put YOUR GitHub repo URL here
  [string]$RepoDir  = "AWS-Prod"
)

$ErrorActionPreference = "Stop"

# Your functions by package type
$ZipFuncs = @(
  "Nightly_Production",
  "Production_Post_Test",
  "Production_Cleanup"
)

$ImageFuncs = @(
  "Production_Transcribe_Sagemaker",
  "Production_Parallel",
  "Production_MP3_WAV",
  "Production_Post"
)

# Create working dirs
New-Item -ItemType Directory -Force -Path "$RepoDir/lambda" | Out-Null
New-Item -ItemType Directory -Force -Path "$RepoDir/containers" | Out-Null
Set-Location $RepoDir

# .gitignore
@"
# Python
__pycache__/
*.pyc
.venv/
venv/
.env

# Node
node_modules/

# General
*.log
*.zip
.DS_Store

# AWS / secrets
.aws/
*.pem
*.key
*.crt
"@ | Out-File .gitignore -Encoding utf8

Write-Host "==> Exporting ZIP-based Lambdas..."
foreach ($fn in $ZipFuncs) {
  Write-Host "   - $fn"
  $url = aws lambda get-function --function-name $fn --region $Region --query "Code.Location" --output text
  New-Item -ItemType Directory -Force -Path "lambda/$fn" | Out-Null
  $zipPath = "$env:TEMP\$fn.zip"
  Invoke-WebRequest -Uri $url -OutFile $zipPath
  Expand-Archive -Path $zipPath -DestinationPath "lambda/$fn" -Force
  Remove-Item $zipPath -Force

  $runtime = aws lambda get-function-configuration --function-name $fn --region $Region --query "Runtime" --output text
  if (-not (Test-Path "lambda/$fn/requirements.txt")) { New-Item "lambda/$fn/requirements.txt" | Out-Null }
  if (-not (Test-Path "lambda/$fn/README.md")) { "# $fn`n`nExported from AWS Lambda ($runtime)" | Out-File "lambda/$fn/README.md" -Encoding utf8 }
}

Write-Host "==> Processing Image-based Lambdas..."
$DockerAvailable = $false
if (Get-Command docker -ErrorAction SilentlyContinue) { $DockerAvailable = $true }

foreach ($fn in $ImageFuncs) {
  Write-Host "   - $fn"
  $imageUri = aws lambda get-function-configuration --function-name $fn --region $Region --query "Code.ImageUri" --output text
  New-Item -ItemType Directory -Force -Path "containers/$fn" | Out-Null
  $imageUri | Out-File "containers/$fn/IMAGE_URI.txt" -Encoding utf8
  if (-not (Test-Path "containers/$fn/README.md")) {
    "# $fn (Image Lambda)`n`n**ImageUri:** $imageUri`n`nIf Docker is available, code is typically at /var/task inside the image." | Out-File "containers/$fn/README.md" -Encoding utf8
  }

  if ($DockerAvailable) {
    try {
      Write-Host "     Docker detected. Pulling and extracting /var/task ..."
      docker pull $imageUri | Out-Null
      $cid = (docker create $imageUri)
      New-Item -ItemType Directory -Force -Path "containers/$fn/code" | Out-Null
      docker cp "$cid`:/var/task" "containers/$fn/code" 2>$null
      docker rm $cid | Out-Null
    } catch {
      Write-Warning "     Could not extract /var/task for $fn (may run from another path)."
    }
  } else {
    Write-Host "     (Note) Docker not found. Skipping code extraction. IMAGE_URI recorded."
  }
}

Write-Host "==> Writing minimal SAM template stub..."
New-Item -ItemType Directory -Force -Path "infra" | Out-Null
@"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Lambda functions (ZIP + Image) exported to source control.

Globals:
  Function:
    Timeout: 60
    MemorySize: 512
    Tracing: Active

Resources:
  NightlyProduction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Nightly_Production
      PackageType: Zip
      CodeUri: ../lambda/Nightly_Production/
      Handler: app.lambda_handler
      Runtime: python3.13

  ProductionPostTest:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_Post_Test
      PackageType: Zip
      CodeUri: ../lambda/Production_Post_Test/
      Handler: app.lambda_handler
      Runtime: python3.13

  ProductionCleanup:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_Cleanup
      PackageType: Zip
      CodeUri: ../lambda/Production_Cleanup/
      Handler: app.lambda_handler
      Runtime: python3.13

  ProductionTranscribeSagemaker:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_Transcribe_Sagemaker
      PackageType: Image
      ImageUri: !Sub "{{resolve:ssm:/sca/lambda/Production_Transcribe_Sagemaker/image-uri}}"

  ProductionParallel:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_Parallel
      PackageType: Image
      ImageUri: !Sub "{{resolve:ssm:/sca/lambda/Production_Parallel/image-uri}}"

  ProductionMP3WAV:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_MP3_WAV
      PackageType: Image
      ImageUri: !Sub "{{resolve:ssm:/sca/lambda/Production_MP3_WAV/image-uri}}"

  ProductionPost:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: Production_Post
      PackageType: Image
      ImageUri: !Sub "{{resolve:ssm:/sca/lambda/Production_Post/image-uri}}"
"@ | Out-File "infra\template-sam.yaml" -Encoding utf8

Write-Host "==> Git init & push..."
git init | Out-Null
git add . | Out-Null
git commit -m "Initial import of AWS Lambda functions (ZIP + Image)" | Out-Null
git branch -M main
git remote add origin $RepoUrl
git push -u origin main

Write-Host ""
Write-Host "Done!"
Write-Host "ZIP code in .\lambda\<fn>\, image URIs (and code if extracted) in .\containers\<fn>\"
Write-Host "SAM stub: .\infra\template-sam.yaml"
