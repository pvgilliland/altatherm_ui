
# Example usage: .\checkin.ps1 -Message "Added new oven UI theme system" -Tag "v1.1.0"

param(
    [string]$Message = "Update",
    [string]$Tag = ""
)

# Ensure we are in the repo folder
Write-Host "== Git Status ==" -ForegroundColor Cyan
git status

Write-Host "`n== Adding files ==" -ForegroundColor Cyan
git add .

Write-Host "`n== Committing ==" -ForegroundColor Cyan
git commit -m "$Message"

Write-Host "`n== Pushing to origin main ==" -ForegroundColor Cyan
git push origin main

if ($Tag -ne "") {
    Write-Host "`n== Creating annotated tag $Tag ==" -ForegroundColor Cyan

    # Create annotated tag using commit message as tag message
    git tag -a $Tag -m "$Message"

    Write-Host "== Pushing tag $Tag ==" -ForegroundColor Cyan
    git push origin $Tag

    Write-Host "✅ Tag $Tag pushed with message: $Message"
}
else {
    Write-Host "No tag supplied, skipping tagging"
}
