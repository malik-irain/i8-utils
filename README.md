Dans ce dépot, vous trouverez le protocoles et les outils développés dans le cadre du projet [eCOnect](https://econect.cnrs.fr/).
C'est un projet européen étudiant la biodiversité dans la région Occitanie. Plusieurs capteurs sont déployés et certains d'entre eux nécessitant un moyen d'envoyer des images avec une vitesse relativement correcte et une faible consommation d'énergie. Pour ce faire, nous utilisons des modules [Digi XBee 3 PRO](https://www.digi.com/products/models/xb3-24z8st) connectés via un adaptateur UART/USB à un ordinateur [Jetson Nano](https://developer.nvidia.com/EMBEDDED/jetson-nano-developer-kit "Jetson Nano official webpage") ou [Raspberry Pi](https://www.raspberrypi.org/ "Raspberry Pi official website"). Cet ordinateur agit comme une passerelle entre les capteurs et notre plateforme cloud, transférant les données reçues du lien de données IEEE 802.15.4 vers Internet, en utilisant une connexion mobile.

Ce projet fournit une couche simplifiée Réseau/Transport (I8TL) pour répondre à nos besoins. Elle permet de transférer des données de manière fiable des dispositifs finaux à un coordinateur, de fragmenter et réassembler des morceaux de données, tout en masquant la complexité aux utilisateurs. Des implémentations de [NeoCayenneLPP](https://neocampus.univ-tlse3.fr/_media/lora/neocayennelpp_lorawan-data-exchange.pdf "NeoCayenneLPP datasheet") et d'un simple wrapper de transfert de fichiers (F8Wrapper) permettant de conserver des attributs du fichier de bout en bout sont également incluses.
