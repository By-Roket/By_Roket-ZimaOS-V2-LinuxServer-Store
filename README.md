# By Roket LinuxServer Store for ZimaOS V2

Boutique communautaire LinuxServer.io pour ZimaOS V2, synchronisée automatiquement depuis le catalogue WisdomSky.

Community LinuxServer.io application store for ZimaOS V2, automatically synchronized from the WisdomSky catalog.

## Français

Cette boutique importe les applications LinuxServer.io, convertit leurs manifests vers le protocole ZimaOS V2, vérifie leur compatibilité avec le validateur officiel, puis génère et publie la distribution officielle.

Le dépôt conserve les sources converties dans `Apps/`. La branche `gh-pages` contient uniquement les fichiers générés de la boutique :

```text
store.json
store.fr_FR.json
index.json
apps/<identifiant>/docker-compose.yml
apps/<identifiant>/meta.json
apps/<identifiant>/assets/
metadata.tar.gz
metadata.sha256
```

Adresse publique prévue après activation de GitHub Pages :

`https://by-roket.github.io/By_Roket-ZimaOS-V2-LinuxServer-Store/store.json`

La synchronisation est lancée automatiquement lors d'une modification du dépôt, tous les jours à 03:17 UTC, ou manuellement depuis GitHub Actions.

Le fuseau horaire `$TZ` présent dans les applications est conservé : ZimaOS reste responsable de fournir sa valeur lors de l'installation.

## English

This store imports LinuxServer.io applications, converts their manifests to the ZimaOS V2 protocol, validates them with the official validator, and generates the official static store distribution.

Converted source manifests are committed under `Apps/`. Generated store files are published to the `gh-pages` branch.

Expected public store URL after enabling GitHub Pages:

`https://by-roket.github.io/By_Roket-ZimaOS-V2-LinuxServer-Store/store.json`

Synchronization runs after relevant repository changes, every day at 03:17 UTC, or manually through GitHub Actions.

The original `$TZ` environment placeholder is preserved so ZimaOS can supply the correct runtime timezone.

## Sources and license

- Upstream catalog: [WisdomSky/CasaOS-LinuxServer-AppStore](https://github.com/WisdomSky/CasaOS-LinuxServer-AppStore)
- Official builder: [IceWhaleTech/build-appstore-action](https://github.com/IceWhaleTech/build-appstore-action)
- License: GNU General Public License v3.0. See [LICENSE](LICENSE).
