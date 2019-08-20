ComicBookMaker
==============

Script to fetch webcomics, archive them and use them to create ebooks.

[![Build Status](https://travis-ci.org/SylvainDe/ComicBookMaker.svg?branch=master)](https://travis-ci.org/SylvainDe/ComicBookMaker)

[![Quantified Code](https://www.quantifiedcode.com/api/v1/project/f7965ba082d64dd5b87181bea6275a80/badge.svg)](https://www.quantifiedcode.com/app/project/f7965ba082d64dd5b87181bea6275a80)

[![Code Climate](https://codeclimate.com/github/SylvainDe/ComicBookMaker/badges/gpa.svg)](https://codeclimate.com/github/SylvainDe/ComicBookMaker) / [![Issue Count](https://codeclimate.com/github/SylvainDe/ComicBookMaker/badges/issue_count.svg)](https://codeclimate.com/github/SylvainDe/ComicBookMaker)

[![Codacy](https://api.codacy.com/project/badge/Grade/6348e7509d804670824a20eb6f6ec169)](https://www.codacy.com/app/sylvain-desodt-github/ComicBookMaker?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=SylvainDe/ComicBookMaker&amp;utm_campaign=Badge_Grade)

[![Scrutinizer](https://scrutinizer-ci.com/g/SylvainDe/ComicBookMaker/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/SylvainDe/ComicBookMaker/?branch=master)

[![Landscape.io](https://landscape.io/github/SylvainDe/ComicBookMaker/master/landscape.svg?style=flat)](https://landscape.io/github/SylvainDe/ComicBookMaker/master)

Longer explanation
------------------

Web crawlers are defined to retrieve comic information and store them into files. This can then be used to generated ebooks.

These webcrawlers are supposed to be easy to write with a minimal amount of boilerplate code whilst trying to keep some flexibility.

Under the hood, there is one class per webcrawler, each of them inherits, directly or not, from an abstract class `GenericComic` which handles all the common logic. Each webcrawler just needs to provide specific information (`name` and `url`) and a way to get the comics after a given one (if any) which is done by implementing the `get_next_comic` generator.

Other abstract classes, inheriting from `GenericComic` provide a convenient way to define `get_next_comic`. The most common is `GenericNavigableComic`, used for comics where next/previous strips are available using the relevant link.

The whole project relies heavily on BeautifulSoup.

Command-line interface
----------------------
`comicbookmaker.py` takes multiple arguments.
 * `--comic` (or `-c`) can be used to tell which comic(s) is/are to be considered (defaults to all of them).
 * `--action` (or `-a`) specifies which actions are to be performed on these comics : update (default behavior), book, etc.


See also
--------
[dosage](http://dosage.rocks/) is a project with similar purpose. It seems to be a very nice project but it doesn't handle ebooks generation.


Contributing
------------

Feel free to open issues/open pull requests/ask questions/give comments.

Here is the little to know before contributing :
 - license is MIT
 - all pep8 rules apply except for the length of the lines


Comics supported
----------------
 * [1111 Comics](http://www.1111comics.me)
 * [1111 Comics (from Tapastic)](https://tapastic.com/series/1111-Comics)
 * [1111 Comics (from Tumblr)](http://comics1111.tumblr.com)
 * [Abstruse Goose](http://abstrusegoose.com)
 * [Tales of Absurdity](http://talesofabsurdity.com)
 * [Tales of Absurdity (from Tapastic)](http://tapastic.com/series/Tales-Of-Absurdity)
 * [Tales of Absurdity (from Tumblr)](http://talesofabsurdity.tumblr.com)
 * [Absurdo](https://absurdo.lapin.org)
 * [Alex Levesque](https://alexlevesque.com)
 * [Angry At Nothing](http://www.angryatnothing.net)
 * [Angry At Nothing (from Tapastic)](http://tapastic.com/series/Comics-yeah-definitely-comics-)
 * [Angry At Nothing (from Tumblr)](http://angryatnothing.tumblr.com)
 * [Anomaly Town (from Tumblr)](https://anomalytown.tumblr.com)
 * [Anything Comic](http://www.anythingcomic.com)
 * [Anything Comic (from Tapastic)](http://tapastic.com/series/anything)
 * [Argyle Sweater](http://www.gocomics.com/theargylesweater)
 * [Amazing Super Powers](http://www.amazingsuperpowers.com)
 * [At Random Comics](http://www.atrandomcomics.com)
 * [Aurel](http://aurel.blog.lemonde.fr)
 * [Space Avalanche](http://www.spaceavalanche.com)
 * [Avventura](http://lavventura.blog.lemonde.fr)
 * [Ma vie est tout a fait fascinante (Bagieu)](https://www.penelope-jolicoeur.com)
 * [Banana Twinky](https://bananatwinky.tumblr.com)
 * [BarteNerds (from Tapastic)](https://tapastic.com/series/BarteNERDS)
 * [Jim Benton](http://www.gocomics.com/jim-benton-cartoons)
 * [Berkeley Mews](http://www.berkeleymews.com)
 * [Berkeley Mews (from GoComics)](http://www.gocomics.com/berkeley-mews)
 * [Berkeley Mews (from Tumblr)](http://mews.tumblr.com)
 * [BFGFS (from Tapastic)](https://tapastic.com/series/BFGFS)
 * [BFGFS (from Tumblr)](https://bfgfs.tumblr.com)
 * [Big Foot Justice](http://bigfootjustice.com)
 * [Big Foot Justice (from Tapastic)](http://tapastic.com/series/bigfoot-justice)
 * [Biter Comics](http://www.bitercomics.com)
 * [Blazers At Dawn](http://blazersatdawn.tumblr.com)
 * [Every Day Blues](http://everydayblues.net)
 * [Books of Adam](http://booksofadam.tumblr.com)
 * [Boulet Corp](http://www.bouletcorp.com)
 * [Boulet Corp (from Tumblr)](https://bouletcorp.tumblr.com)
 * [Boulet Corp English](http://english.bouletcorp.com)
 * [Boumeries (from Tumblr)](http://boumeries.tumblr.com/)
 * [Boumeries (En)](http://comics.boumerie.com)
 * [Boumeries (Fr)](http://bd.boumerie.com)
 * [Break Of Day](http://www.gocomics.com/break-of-day)
 * [Brevity](http://www.gocomics.com/brevity)
 * [Brooklyn Cartoons (from Tumblr)](http://brooklyncartoons.tumblr.com)
 * [BuniComics](http://www.bunicomic.com)
 * [Electric Bunny Comic](http://www.electricbunnycomics.com/View/Comic/153/Welcome+to+Hell)
 * [Electric Bunny Comic (from Tumblr)](http://electricbunnycomics.tumblr.com)
 * [ButterSafe](https://www.buttersafe.com)
 * [Calvin and Hobbes](http://marcel-oehler.marcellosendos.ch/comics/ch/)
 * [Calvin and Hobbes (from GoComics)](http://www.gocomics.com/calvinandhobbes)
 * [Cancer Owl (from Tumblr)](http://cancerowl.tumblr.com)
 * [Is It Canon (from Tapastic)](http://tapastic.com/series/isitcanon)
 * [Cassandra Calin (from Tapastic)](https://tapas.io/series/CassandraComics)
 * [Cassandra Calin (from Tumblr)](http://c-cassandra.tumblr.com)
 * [Catana](http://www.catanacomics.com)
 * [Caw4hw (from Tapastic)](https://tapas.io/series/CAW4HW)
 * [Caw4hw (from Tumblr)](https://caw4hw.tumblr.com)
 * [Channelate](http://www.channelate.com)
 * [Cheese Cornz (from Tumblr)](https://cheesecornz.tumblr.com)
 * [Chuckle-A-duck](http://chuckleaduck.com)
 * [Cinismo Ilustrado](http://cinismoilustrado.com)
 * [Victims Of Circumsolar](http://www.victimsofcircumsolar.com)
 * [Victims Of Circumsolar (from Tumblr)](https://victimsofcomics.tumblr.com)
 * [A Comik](https://acomik.com)
 * [Commit Strip (En)](http://www.commitstrip.com/en)
 * [Commit Strip (Fr)](http://www.commitstrip.com/fr)
 * [Over Compensating](http://www.overcompensating.com)
 * [Completely Serious Comics](http://completelyseriouscomics.com)
 * [consolia](https://consolia-comic.com)
 * [Joan Cornella (from Tumblr)](http://cornellajoan.tumblr.com)
 * [Cowardly Comics (from Tapastic)](https://tapas.io/series/CowardlyComics)
 * [Cowardly Comics (from Tumblr)](http://cowardlycomics.tumblr.com)
 * [C Est Pas En Regardant Ses Pompes (...)](http://marcoandco.tumblr.com)
 * [Cube Drone](http://cube-drone.com/comics)
 * [Cheer Up Emo Kid (from Tapastic)](http://tapastic.com/series/CUEK)
 * [Cheer Up Emo Kid (from Tumblr)](https://enzocomics.tumblr.com)
 * [Les Culottees](http://lesculottees.blog.lemonde.fr)
 * [Cyanide and Happiness](http://explosm.net)
 * [Dagsson Hugleikur (from Tumblr)](https://hugleikurdagsson.tumblr.com)
 * [Dakota McDadzean](http://dakotamcfadzean.tumblr.com)
 * [Deadly Panel](http://www.deadlypanel.com)
 * [Deadly Panel (from Tapastic)](https://tapastic.com/series/deadlypanel)
 * [Deadly Panel (from Tumblr)](https://deadlypanel.tumblr.com)
 * [Death Bulge](http://www.deathbulge.com)
 * [Deep Dark Fears (from Tumblr)](http://deep-dark-fears.tumblr.com)
 * [Depressed Alien](http://depressedalien.com)
 * [According To Devin](http://accordingtodevin.tumblr.com)
 * [Mr Ethan Diamond](http://mrethandiamond.tumblr.com)
 * [Dilbert](http://dilbert.com)
 * [Ali Dilem](http://information.tv5monde.com/dilem)
 * [Dinosaur Comics](http://www.qwantz.com)
 * [Disco Bleach](http://discobleach.com)
 * [The Dog House Diaries](http://thedoghousediaries.com)
 * [Dogmo Dog](http://www.dogmodog.com)
 * [Don't Be Dad (from Tapastic)](https://tapas.io/series/DontBeDad-Comics)
 * [Doodle For Food](https://www.doodleforfood.com)
 * [Doodle For Food (from Tapastic)](https://tapastic.com/series/Doodle-for-Food)
 * [Dorris Mc](https://dorrismccomics.com)
 * [Dorris Mc (from GoComics)](http://www.gocomics.com/dorris-mccomics)
 * [Doug Was Taken](https://dougwastaken.tumblr.com)
 * [Dustinteractive](https://dustinteractive.com)
 * [The Earth Explodes](http://www.earthexplodes.com)
 * [Eat My Paint (from Tapastic)](https://tapas.io/series/eatmypaint)
 * [Eat My Paint (from Tumblr)](https://eatmypaint.tumblr.com)
 * [Extra Fabulous Comics](http://extrafabulouscomics.com)
 * [Extra Fabulous Comics (from Tumblr)](https://extrafabulouscomics.tumblr.com)
 * [Safely Endangered](https://www.safelyendangered.com)
 * [Safely Endangered (from Tumblr)](https://tumblr.safelyendangered.com)
 * [Eve Velo - chroniques du velotaf](http://evevelo.the-comic.org)
 * [My Extra Life](http://www.myextralife.com)
 * [Fat Awesome](http://fatawesome.com/comics)
 * [Fat Awesome (from Tumblr)](http://fatawesomecomedy.tumblr.com)
 * [The World Is Flat (from Tapastic)](https://tapastic.com/series/The-World-is-Flat)
 * [The World Is Flat (from Tumblr)](https://theworldisflatcomics.com)
 * [floccinaucinihilipilification](http://floccinaucinihilipilificationa.tumblr.com)
 * [Cartooning For Peace](http://cartooningforpeace.blog.lemonde.fr)
 * [Fowl Language Comics (from GoComics)](http://www.gocomics.com/fowl-language)
 * [Fowl Language Comics (from Tapastic)](http://tapastic.com/series/Fowl-Language-Comics)
 * [Fowl Language Comics (from Tumblr)](http://fowllanguagecomics.tumblr.com)
 * [FoxTrot](http://www.gocomics.com/foxtrot)
 * [FoxTrot Classics](http://www.gocomics.com/foxtrotclassics)
 * [Mrs Frollein (from Tumblr)](https://mrsfrollein.tumblr.com)
 * [Garfield](https://garfield.com)
 * [Garfield (from GoComics)](http://www.gocomics.com/garfield)
 * [Geek And Poke](http://geek-and-poke.com)
 * [Gemma Correll (from Tumblr)](http://gemmacorrell.tumblr.com)
 * [The Gentleman Armchair](http://thegentlemansarmchair.com)
 * [Gerbil With A Jetpack](http://gerbilwithajetpack.com)
 * [Glory Owl](http://gloryowlcomix.blogspot.fr)
 * [Good Bear Comics (from Tumblr)](https://goodbearcomics.tumblr.com)
 * [Xavier Gorce](http://xaviergorce.blog.lemonde.fr)
 * [The Grohl Troll](http://thegrohltroll.com)
 * [Chris Hallback (from Tumblr)](https://chrishallbeck.tumblr.com)
 * [Chris Hallback - The Book of Biff (from Tapastic)](https://tapastic.com/series/Biff)
 * [Chris Hallback - Maximumble (from Tapastic)](https://tapastic.com/series/Maximumble)
 * [Chris Hallback - Minimumble (from Tapastic)](https://tapastic.com/series/Minimumble)
 * [A Hamm A Day](http://www.ahammaday.com)
 * [Happle Tea](http://www.happletea.com)
 * [Hark A Vagrant (from Tumblr)](http://beatonna.tumblr.com)
 * [Heck if I Know comics (from Tapastic)](http://tapastic.com/series/Regular)
 * [Heck if I Know comics (from Tumblr)](http://heckifiknowcomics.com)
 * [Hit and Miss Comics](https://hitandmisscomics.tumblr.com)
 * [HM Blanc](http://hmblanc.tumblr.com)
 * [Hoomph](http://hoom.ph)
 * [Horovitz (from Tumblr)](https://horovitzcomics.tumblr.com)
 * [Horovitz Classic](http://www.horovitzcomics.com)
 * [Horovitz New](http://www.horovitzcomics.com)
 * [Hot Comics For Cool People (from Tapastic)](https://tapastic.com/series/Hot-Comics-For-Cool-People)
 * [Hot Comics For Cool People (from Tumblr)](http://hotcomicsforcoolpeople.tumblr.com)
 * [Huffy Penguin](http://huffy-penguin.tumblr.com)
 * [Ice Cream Sandwich Comics](https://icecreamsandwichcomics.com)
 * [Imogen Quest](http://imogenquest.net)
 * [Imogen Quest (from GoComics)](https://www.gocomics.com/imogen-quest)
 * [Imogen Quest (from Tumblr)](http://imoquest.tumblr.com)
 * [Incidental Comics (from Tumblr)](http://incidentalcomics.tumblr.com)
 * [Infinite Guff](http://infiniteguff.com)
 * [Infinite Immortal Bens (from Tapastic)](https://tapas.io/series/Infinite-Immortal-Bens)
 * [Infinite Immortal Bens (from Tumblr)](https://infiniteimmortalbens.tumblr.com)
 * [Invisible Bread](http://invisiblebread.com)
 * [In Your Face Cake (from Tapastic)](https://tapas.io/series/In-Your-Face-Cake)
 * [In Your Face Cake (from Tumblr)](https://in-your-face-cake.tumblr.com)
 * [Irwin Cardozo](http://irwincardozocomics.tumblr.com)
 * [It Fools A Monster](http://itfoolsamonster.com)
 * [Jake Likes Onions](https://jakelikesonions.com)
 * [James Of No Trades (from Tapastic)](https://tapas.io/series/James-of-No-Trades)
 * [James Of No Trades (from Tumblr)](http://jamesfregan.tumblr.com)
 * [My Jet Pack](http://myjetpack.tumblr.com)
 * [Jhall Comics (from Tumblr)](http://jhallcomics.tumblr.com)
 * [Joey Alison Sayers (from GoComics)](http://www.gocomics.com/joey-alison-sayers-comics)
 * [Julia's Drawings](https://drawings.jvns.ca)
 * [Just Say Eh](http://www.justsayeh.com)
 * [Just Say Eh (from Tapastic)](http://tapastic.com/series/Just-Say-Eh)
 * [Kickstand Comics featuring Yehuda Moon](http://yehudamoon.com)
 * [For Lack Of A Better Comic](http://forlackofabettercomic.tumblr.com)
 * [Last Place Comics](http://lastplacecomics.com)
 * [Leleoz (from Tapastic)](https://tapastic.com/series/Leleoz)
 * [Leleoz (from Tumblr)](http://leleozcomics.tumblr.com)
 * [LibraryComic (from Tumblr)](https://librarycomic.tumblr.com)
 * [Little Life Lines](http://www.littlelifelines.com)
 * [Little Life Lines (from Tumblr)](https://little-life-lines.tumblr.com)
 * [Light Roast Comics](http://lightroastcomics.com)
 * [Light Roast Comics (from Tapastic)](https://tapas.io/series/Light-Roast-Comics)
 * [L.I.N.S. Editions](https://linsedition.com)
 * [L.I.N.S. Editions (from Tumblr)](https://linscomics.tumblr.com)
 * [Loading Artist](http://www.loadingartist.com/latest)
 * [Lol Nein (from Tumblr)](http://lolneincom.tumblr.com)
 * [Mike Luckovich](http://www.gocomics.com/mikeluckovich)
 * [Lunar Baboon](http://www.gocomics.com/lunarbaboon)
 * [Une Annee au Lycee](http://uneanneeaulycee.blog.lemonde.fr)
 * [Macadam Valley](http://macadamvalley.com)
 * [Lisa Mandel (HP, hors-service)](http://lisamandel.blog.lemonde.fr)
 * [Man Versus Manatee](http://manvsmanatee.com)
 * [Marketoonist](https://marketoonist.com/cartoons)
 * [The Meerkatguy](http://www.themeerkatguy.com)
 * [Mercworks](http://mercworks.net)
 * [Mercworks (from Tapastic)](https://tapastic.com/series/MercWorks)
 * [Mercworks (from Tumblr)](http://mercworks.tumblr.com)
 * [Micael (L'Air du temps)](https://www.lemonde.fr/blog/micael/)
 * [Lonnie Millsap](http://www.lonniemillsap.com)
 * [Mister & Me](http://www.mister-and-me.com)
 * [Mister & Me (from GoComics)](http://www.gocomics.com/mister-and-me)
 * [Mister & Me (from Tapastic)](https://tapastic.com/series/Mister-and-Me)
 * [Art By Moga](http://artbymoga.tumblr.com)
 * [Momentum (from Tapastic)](https://tapastic.com/series/momentum)
 * [Infinite Monkey Business](http://infinitemonkeybusiness.net)
 * [Monkey User](http://www.monkeyuser.com)
 * [Moon Beard](https://moonbeard.com)
 * [Moon Beard (from Tumblr)](http://squireseses.tumblr.com)
 * [Tu Mourras Moins Bete](http://tumourrasmoinsbete.blogspot.fr)
 * [Mouse Bear Comedy](http://www.mousebearcomedy.com/category/comics/)
 * [Mouse Bear Comedy (from Tumblr)](http://mousebearcomedy.tumblr.com)
 * [Mr. Lovenstein](http://www.mrlovenstein.com)
 * [Mr. Lovenstein (from Tapastic)](https://tapastic.com/series/MrLovenstein)
 * [NamelessPCs (from Tapastic)](https://tapastic.com/series/NamelessPC)
 * [Morgan Navarro (Ma vie de reac)](http://morgannavarro.blog.lemonde.fr)
 * [NeDroid](http://nedroid.com)
 * [Nelluc Nhoj](https://nellucnhoj.com)
 * [Nick Anderson](http://www.gocomics.com/nickanderson)
 * [Non Sequitur](http://www.gocomics.com/nonsequitur)
 * [Nothing Suspicious](https://nothingsuspicio.us)
 * [Comic Nuggets](https://comicnuggets.com)
 * [The Oatmeal (from Tumblr)](http://oatmeal.tumblr.com)
 * [Octopuns](http://www.octopuns.net)
 * [Octopuns (from Tumblr)](http://octopuns.tumblr.com)
 * [Off The Leash Dog](http://offtheleashdogcartoons.com)
 * [Off The Leash Dog (from Tumblr)](http://rupertfawcettsdoggyblog.tumblr.com)
 * [Off The Mark](http://www.gocomics.com/offthemark)
 * [Oglaf [NSFW]](http://oglaf.com)
 * [One Giant Hand](http://onegianthand.com)
 * [Optipess](http://www.optipess.com)
 * [Endless Origami](http://endlessorigami.com)
 * [Origami Hot Dish](http://origamihotdish.com)
 * [Oscillating Profundities](http://tapastic.com/series/oscillatingprofundities)
 * [Owl Turd / Shen Comix (from GoComics)](https://www.gocomics.com/shen-comix)
 * [Owl Turd / Shen Comix (from Tapastic)](https://tapas.io/series/Shen-Comix)
 * [Owl Turd / Shen Comix (from Tumblr)](https://shencomix.tumblr.com)
 * [Pain Train Comics](http://paintraincomic.com)
 * [Perry Bible Fellowship](http://pbfcomics.com)
 * [Peanuts](http://www.gocomics.com/peanuts)
 * [Pearls Before Swine](http://www.gocomics.com/pearlsbeforeswine)
 * [Pear-Shaped Comics](http://pearshapedcomics.com)
 * [Penmen](http://penmen.com)
 * [Peter Lauris](http://peterlauris.com/comics)
 * [PhD Comics](http://phdcomics.com/comics/archive.php)
 * [Pictures in Boxes](http://www.picturesinboxes.com)
 * [Pictures in Boxes (from Tumblr)](https://picturesinboxescomic.tumblr.com)
 * [Pie Comic](http://piecomic.tumblr.com)
 * [The Pigeon Gazette (from Tapastic)](https://tapastic.com/series/The-Pigeon-Gazette)
 * [The Pigeon Gazette (from Tumblr)](http://thepigeongazette.tumblr.com)
 * [Plan C](http://www.plancomic.com)
 * [Plantu](http://plantu.blog.lemonde.fr)
 * [Pleasant Thoughts](http://pleasant-thoughts.com)
 * [A Pleasant Waste Of Time (from Tapastic)](https://tapas.io/series/A-Pleasant-)
 * [A Pleasant Waste Of Time (from Tumblr)](https://artjcf.tumblr.com)
 * [Pom Comics / Piece of Me](http://www.pomcomic.com)
 * [Pond Scum](http://pondscumcomic.tumblr.com)
 * [Poorly Drawn Lines](https://www.poorlydrawnlines.com)
 * [Poorly Drawn Lines (from Tumblr)](http://pdlcomics.tumblr.com)
 * [Yesterday's Popcorn (from Tapastic)](https://tapastic.com/series/Yesterdays-Popcorn)
 * [Yesterday's Popcorn (from Tumblr)](http://yesterdayspopcorn.tumblr.com)
 * [Pretends to be drawing](https://ptbd.jwels.berlin)
 * [Pretends to be drawing (from Tapastic)](https://tapas.io/series/ptbd)
 * [Pundemonium](http://monstika.tumblr.com)
 * [Quarktees](http://www.quarktees.com/blogs/news)
 * [Rae the Doe](https://www.raethedoe.com)
 * [Rae the Doe (from Tumblr)](https://raethedoe.tumblr.com)
 * [Ted Rall](http://rall.com/comic)
 * [Ted Rall (from GoComics)](http://www.gocomics.com/ted-rall)
 * [Michael Ramirez](http://www.gocomics.com/michaelramirez)
 * [Random Crab](https://randomcrab.com)
 * [RandoWis (from Tapastic)](https://tapastic.com/series/RandoWis)
 * [Classic Randy](http://classicrandy.tumblr.com)
 * [Gone Into Rapture](http://goneintorapture.com)
 * [Gone Into Rapture (from Tapastic)](http://tapastic.com/series/Goneintorapture)
 * [Respawn Comic](http://respawncomic.com )
 * [Respawn Comic (from Tumblr)](https://respawncomic.tumblr.com)
 * [Rustled Jimmies](http://rustledjimmies.net)
 * [Robbie And Bobby (from Tumblr)](http://robbieandbobby.tumblr.com)
 * [Robospunk](http://robospunk.com)
 * [Robotatertot (from Tumblr)](https://robotatertot.tumblr.com)
 * [Mandatory Roller Coaster](https://mandatoryrollercoaster.com)
 * [Rory (from Tapastic)](https://tapas.io/series/rorycomics)
 * [Rory (from Tumblr)](https://rorycomics.tumblr.com)
 * [Rock Paper Cynic (from Tapastic)](https://tapastic.com/series/rockpapercynic)
 * [Rock Paper Cynic (from Tumblr)](http://rockpapercynic.tumblr.com)
 * [Rock Paper Scissors](http://rps-comics.com)
 * [Sarah Andersen (from GoComics)](http://www.gocomics.com/sarahs-scribbles)
 * [Sarah Andersen (from Tapastic)](http://tapastic.com/series/Doodle-Time)
 * [Scandinavia And The World](http://satwcomic.com)
 * [Savage Chicken (from GoComics)](http://www.gocomics.com/savage-chickens)
 * [Sephko](https://sephko.tumblr.com)
 * [Sheldon Comics](http://www.sheldoncomics.com)
 * [Sheldon Comics (from GoComics)](http://www.gocomics.com/sheldon)
 * [Shitfest](http://shitfestcomic.com)
 * [Sinewyn (from Tumblr)](https://sinewyn.tumblr.com)
 * [Skeleton Claw](http://skeletonclaw.com)
 * [Small Blue Yonder (from Tapastic)](https://tapastic.com/series/Small-Blue-Yonder)
 * [Saturday Morning Breakfast Cereal](http://www.smbc-comics.com)
 * [Saturday Morning Breakfast Cereal (from GoComics)](http://www.gocomics.com/saturday-morning-breakfast-cereal)
 * [Saturday Morning Breakfast Cereal (from Tumblr)](http://smbc-comics.tumblr.com)
 * [Something Of That Ilk](http://www.somethingofthatilk.com)
 * [Down the Upward Spiral (from Tapastic)](https://tapastic.com/series/Down-the-Upward-Spiral)
 * [Down the Upward Spiral (from Tumblr)](http://downtheupwardspiral.tumblr.com)
 * [Things in squares](http://www.thingsinsquares.com)
 * [Sticky Cinema Floor](https://stickycinemafloor.tumblr.com)
 * [Make it stoopid](http://makeitstoopid.com/comic.php)
 * [Everything's Stupid](http://everythingsstupid.net)
 * [Everything's Stupid (from Tapastic)](http://tapastic.com/series/EverythingsStupid)
 * [Sunny Street](http://www.gocomics.com/sunny-street)
 * [Our Super Adventure (from Tapastic)](https://tapastic.com/series/Our-Super-Adventure)
 * [Our Super Adventure (from Tumblr)](http://sarahssketchbook.tumblr.com)
 * [System Comic](http://www.systemcomic.com)
 * [Shanghai Tango](http://tango2010weibo.tumblr.com)
 * [The Ism](http://www.theism-comics.com)
 * [The Odd 1s Out (from Tapastic)](https://tapastic.com/series/Theodd1sout)
 * [The Odd 1s Out (from Tumblr)](http://theodd1sout.tumblr.com)
 * [These Inside Jokes (from Tumblr)](http://theseinsidejokes.tumblr.com)
 * [They Can Talk](http://theycantalk.com)
 * [Thor's Thundershack](http://www.thorsthundershack.com)
 * [Thor's Thundershack (from Tapastic)](http://tapastic.com/series/Thors-Thundershac)
 * [Three Word Phrase](http://threewordphrase.com)
 * [Three Word Phrase (from Tumblr)](http://threewordphrase.tumblr.com)
 * [It's the tie](http://itsthetie.com)
 * [It's the tie (from Tapastic)](https://tapastic.com/series/itsthetie)
 * [It's the tie (from Tumblr)](http://itsthetie.tumblr.com)
 * [Time Trabble (from Tumblr)](http://timetrabble.tumblr.com)
 * [Tizzy Stitch Bird (from Tapastic)](https://tapastic.com/series/TizzyStitchbird)
 * [Tizzy Stitch Bird (from Tumblr)](http://tizzystitchbird.tumblr.com)
 * [Tom Toles](http://www.gocomics.com/tomtoles)
 * [Toon Hole](http://www.toonhole.com)
 * [Toon Hole (from Tapastic)](http://tapastic.com/series/TOONHOLE)
 * [Tubey Toons](http://tubeytoons.com)
 * [Tubey Toons (from Tapastic)](http://tapastic.com/series/Tubey-Toons)
 * [Tubey Toons (from Tumblr)](https://tubeytoons.tumblr.com)
 * [Tumblr Dry (from Tapastic)](https://tapastic.com/series/TumbleDryComics)
 * [Turn Off Us](http://turnoff.us)
 * [Twisted Doodles](https://www.twisteddoodles.com)
 * [Ubertool](http://ubertoolcomic.com)
 * [Ubertool (from Tapastic)](https://tapastic.com/series/ubertool)
 * [Ubertool (from Tumblr)](https://ubertool.tumblr.com)
 * [The Underfold (from Tumblr)](http://theunderfold.tumblr.com)
 * [Unearthed Comics](http://unearthedcomics.com)
 * [Unearthed Comics (from Tapastic)](http://tapastic.com/series/UnearthedComics)
 * [Unearthed Comics (from Tumblr)](https://unearthedcomics.tumblr.com)
 * [Up And Out (from Tumblr)](http://upandoutcomic.tumblr.com)
 * [Up And Out (from Tapastic)](http://tapastic.com/series/UP-and-OUT)
 * [As Per Usual (from Tapastic)](https://tapastic.com/series/AsPerUsual)
 * [As Per Usual (from Tumblr)](http://as-per-usual.tumblr.com)
 * [Vector Belly](http://vectorbelly.tumblr.com)
 * [Vegetables For Dessert](http://tapastic.com/series/vegetablesfordessert)
 * [Vidberg - l'actu en patates](http://vidberg.blog.lemonde.fr)
 * [Verbal Vomit (from Tumblr)](http://verbalvomits.tumblr.com)
 * [Waffles And Pancakes](https://tapastic.com/series/Waffles-and-Pancakes)
 * [War And Peas](https://warandpeas.com)
 * [War And Peas (from Tumblr)](http://warandpeas.tumblr.com)
 * [Warehouse Comic](http://warehousecomic.com)
 * [Webcomic Name](https://webcomicname.com)
 * [We Flaps (from Tumblr)](https://weflaps.tumblr.com)
 * [Will 5:00 Never Come ?](http://will5nevercome.com)
 * [Wondermark](http://wondermark.com)
 * [Wooden Plank Studios](https://www.woodenplankstudios.com/comic/)
 * [Matt Wuerker](http://www.gocomics.com/mattwuerker)
 * [WuMo](http://www.gocomics.com/wumo)
 * [xkcd](http://xkcd.com)
 * [The Awkward Yeti](http://theawkwardyeti.com)
 * [The Awkward Yeti (from GoComics)](http://www.gocomics.com/the-awkward-yeti)
 * [The Awkward Yeti (from Tapastic)](https://tapastic.com/series/TheAwkwardYeti)
 * [The Awkward Yeti (from Tumblr)](http://larstheyeti.tumblr.com)
 * [Zen Pencils](http://zenpencils.com)
 * [Zen Pencils (from Tumblr)](http://zenpencils.tumblr.com)
 * [Zep World](http://zepworld.blog.lemonde.fr)
 * [Znoflats Comics](http://tapastic.com/series/Znoflats-Comics)
