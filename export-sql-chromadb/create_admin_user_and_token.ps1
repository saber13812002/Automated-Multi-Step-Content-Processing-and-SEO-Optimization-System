# PowerShell script to create admin user and token
# Make sure the service is running on http://localhost:8080

Write-Host "Creating admin user..." -ForegroundColor Cyan

try {
    $userResponse = Invoke-RestMethod -Uri "http://localhost:8080/admin/auth/users" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body '{"username":"admin","email":"admin@example.com"}'
    
    Write-Host "User response: $($userResponse | ConvertTo-Json)" -ForegroundColor Green
    
    $userId = $userResponse.user_id
    
    if (-not $userId) {
        Write-Host "Failed to create user or extract user_id. Response: $($userResponse | ConvertTo-Json)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "User created with ID: $userId" -ForegroundColor Green
    Write-Host ""
    Write-Host "Creating token..." -ForegroundColor Cyan
    
    # Calculate expiration date: 10 years from now (large number as requested)
    $expiresAt = (Get-Date).AddYears(10).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss")
    
    $tokenBody = @{
        user_id = $userId
        name = "Main Development Token"
        rate_limit_per_day = 1000
        expires_at = $expiresAt
    } | ConvertTo-Json
    
    $tokenResponse = Invoke-RestMethod -Uri "http://localhost:8080/admin/auth/tokens" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $tokenBody
    
    Write-Host "Token response: $($tokenResponse | ConvertTo-Json)" -ForegroundColor Green
    
    $token = $tokenResponse.token
    
    if (-not $token) {
        Write-Host "Failed to extract token. Full response: $($tokenResponse | ConvertTo-Json)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "Token created successfully!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "Token: $token" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Add this to your .env file:" -ForegroundColor Yellow
    Write-Host "API_TOKEN=$token" -ForegroundColor White
    Write-Host "==========================================" -ForegroundColor Yellow
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Make sure the service is running on http://localhost:8080" -ForegroundColor Yellow
    exit 1
}

