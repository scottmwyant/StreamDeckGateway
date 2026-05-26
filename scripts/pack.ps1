#
# Call this script from the root of the project
#

$tmp = "streamdeck"      # Staging directory
$pub = "streamdeck.tar.gz"  # file for distribution

# Clean artifacts
if(Test-Path $tmp) {
    Remove-Item -Path $tmp -Recurse -Force
}
if(Test-Path $pub) {
    Remove-item $pub -Force
}

# Copy source code from external dependencies
Copy-Item -Path "paho\src" -Destination $tmp -Recurse 
Copy-Item -Path "pyhidapi\hid\" -Destination $tmp -Recurse 

# Copy source files from this project
Copy-Item -Path "src\*" -Exclude "test" -Destination $tmp

# Pack
& tar.exe -czf $pub $tmp

# Remove the staging directory
Remove-Item -Path $tmp -Recurse -Force

# List the content of the tarball we just created
Write-Host "`n$pub contains the following:`n"
& tar.exe -tf $pub
Write-Host ""