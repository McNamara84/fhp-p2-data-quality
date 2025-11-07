# R-Pakete für Anreicherungsstatistik installieren

cat("📦 Installiere benötigte R-Pakete...\n\n")

# Benutzer-Library Pfad setzen
user_lib <- Sys.getenv("R_LIBS_USER")
if (!dir.exists(user_lib)) {
  dir.create(user_lib, recursive = TRUE)
  cat(paste("Erstelle Benutzer-Library:", user_lib, "\n"))
}

# Liste der benötigten Pakete
packages <- c("jsonlite", "ggplot2")

# Installiere fehlende Pakete
for (pkg in packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    cat(paste("Installiere", pkg, "...\n"))
    install.packages(pkg, repos = "https://cloud.r-project.org/", lib = user_lib, quiet = FALSE)
  } else {
    cat(paste("✓", pkg, "ist bereits installiert\n"))
  }
}

cat("\n✅ Alle Pakete installiert!\n")
