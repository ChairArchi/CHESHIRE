param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference = 'Stop'
# Reuses Task 12's fixed System.Drawing projection and polygon-light method.
# This is an approximate HEADLESS view of saved polygons, never a Rhino image.
Add-Type -AssemblyName System.Drawing
$plan = Get-Content -Raw -LiteralPath $PlanPath | ConvertFrom-Json
$atlasDirectory = Split-Path -Parent $PlanPath
function Project($p) { return @(([double]$p[0]+0.65*[double]$p[1]), ([double]$p[2]+0.30*[double]$p[1])) }
$brushes = @{}
$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(160,65,75,84)),0.65
$font = New-Object System.Drawing.Font 'Arial',14
$small = New-Object System.Drawing.Font 'Arial',10
$textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(25,35,45))
function Paint-Frame($frame) {
    $mesh = Get-Content -Raw -LiteralPath (Join-Path $atlasDirectory $frame.mesh) | ConvertFrom-Json
    $bounds = $frame.bounds; $cellWidth = [int]$frame.width; $cellHeight = [int]$frame.height
    $bitmap = New-Object System.Drawing.Bitmap $cellWidth,$cellHeight
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.Clear([System.Drawing.Color]::White)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.DrawString('HEADLESS / fixed camera, scale and gray light', $small, $textBrush, 12, 8)
    $g.DrawString($frame.label, $font, $textBrush, 12, 27)
    $scale = [math]::Min(($cellWidth-50)/($bounds[1]-$bounds[0]), ($cellHeight-80)/($bounds[3]-$bounds[2]))
    $g.SetClip((New-Object System.Drawing.Rectangle 5,52,($cellWidth-10),($cellHeight-57)))
    $world = @{}; $screen = @{}
    foreach ($v in $mesh.vertices) {
        $world[[int]$v.id] = $v.xyz
        $p = Project $v.xyz
        $screen[[int]$v.id] = New-Object System.Drawing.PointF ([single](25+($p[0]-$bounds[0])*$scale)),([single](55+($bounds[3]-$p[1])*$scale))
    }
    $ordered = foreach ($face in $mesh.faces) {
        $depth = 0.0
        foreach ($key in $face.vertices) { $v=$world[[int]$key]; $depth += 0.65*$v[0]-$v[1]+0.30*$v[2] }
        @{ Face=$face; Depth=$depth/$face.vertices.Count }
    }
    foreach ($item in ($ordered | Sort-Object -Property Depth)) {
        $face = $item.Face
        $points = [System.Drawing.PointF[]]@(foreach ($key in $face.vertices) { $screen[[int]$key] })
        $a=$world[[int]$face.vertices[0]]; $b=$world[[int]$face.vertices[1]]; $c=$world[[int]$face.vertices[2]]
        $ab=@(($b[0]-$a[0]),($b[1]-$a[1]),($b[2]-$a[2])); $ac=@(($c[0]-$a[0]),($c[1]-$a[1]),($c[2]-$a[2]))
        $nx=$ab[1]*$ac[2]-$ab[2]*$ac[1]; $ny=$ab[2]*$ac[0]-$ab[0]*$ac[2]; $nz=$ab[0]*$ac[1]-$ab[1]*$ac[0]
        $length=[math]::Sqrt($nx*$nx+$ny*$ny+$nz*$nz)
        $gray = if ($length -gt 0) { [int](130+100*[math]::Abs((0.3*$nx-0.8*$ny+0.5*$nz)/$length)) } else { 130 }
        $gray=[math]::Max(0,[math]::Min(255,$gray))
        if (-not $brushes.ContainsKey($gray)) { $brushes[$gray] = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($gray,$gray,$gray)) }
        if (-not $frame.wireframe) { $g.FillPolygon($brushes[$gray], $points) }
        if ($frame.wireframe) { $g.DrawPolygon($pen, $points) }
    }
    $bitmap.Save((Join-Path $atlasDirectory $frame.file),[System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bitmap.Dispose()
    Write-Output $frame.file
}
try {
    foreach ($frame in $plan.frames) { Paint-Frame $frame }
    foreach ($sheet in $plan.sheets) {
        $rows = [int][math]::Ceiling($sheet.images.Count / $sheet.columns)
        $bitmap = New-Object System.Drawing.Bitmap ([int]($sheet.columns*$sheet.width)),([int]($rows*$sheet.height+70))
        $g = [System.Drawing.Graphics]::FromImage($bitmap)
        $g.Clear([System.Drawing.Color]::White)
        $g.DrawString($sheet.title, $font, $textBrush, 12, 8)
        $g.DrawString('HEADLESS actual geometry / all frames share camera, scale, light and registered crop', $small, $textBrush, 12, 35)
        $index = 0
        foreach ($file in $sheet.images) {
            $image = [System.Drawing.Image]::FromFile((Join-Path $atlasDirectory $file))
            try { $g.DrawImageUnscaled($image,([int](($index % $sheet.columns)*$sheet.width)),([int]([math]::Floor($index/$sheet.columns)*$sheet.height+70))) }
            finally { $image.Dispose() }
            $index++
        }
        $bitmap.Save((Join-Path $atlasDirectory $sheet.file),[System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bitmap.Dispose()
        Write-Output $sheet.file
    }
} finally {
    foreach ($brush in $brushes.Values) { $brush.Dispose() }
    $textBrush.Dispose(); $font.Dispose(); $small.Dispose(); $pen.Dispose()
}
