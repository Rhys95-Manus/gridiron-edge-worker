# COA-01 registry sources (review file)

Research for `config/coaching_registry.csv`, 2026 season. Four research agents ran on 2026-10-05 (teams split 1-8, 9-16, 17-24, 25-32); the user approved the rows on 2026-10-07 with these rulings:

- Confidence: `team_or_major` (team site or major outlet), `local_or_team_focused` (local or team-focused outlet), `ranking_only` (a play-caller ranking list only).
- Blank SF offensive coordinator, CAR defensive play-caller, LV offensive play-caller.
- A blank role falls back to the G4 head-coach stand-in.
- `effective_date` = the team's first 2026 regular-season game date from the nflverse schedules table (DATA-04). No in-season changes were found through week 4.

Quotes the fetch tool returned as paraphrase are marked `(summary)` in the CSV; the agents warned that WebFetch can paraphrase, so no quote is guaranteed verbatim. Re-check a cell's page before relying on its exact wording.

## Rows written

149 rows, 32 teams. Confidence counts: team_or_major 125, local_or_team_focused 14, ranking_only 10.

## Blank cells

| team | role | reason |
|---|---|---|
| ARI | defensive_play_caller | no source stated this explicitly |
| ATL | defensive_play_caller | no source stated this explicitly |
| CAR | defensive_play_caller | user: blank (sources conflict) |
| CHI | defensive_play_caller | no source stated this explicitly |
| CIN | defensive_play_caller | no source stated this explicitly |
| LV | offensive_play_caller | user: blank (sources conflict) |
| NYG | defensive_play_caller | no source stated this explicitly |
| PHI | defensive_play_caller | no source stated this explicitly |
| SEA | defensive_play_caller | no source stated this explicitly |
| SF | offensive_coordinator | user: blank (stale source) |
| TB | defensive_coordinator | no source stated this explicitly |

Notes on the filled cells the user should know about:

- GB offensive coordinator: the only source is local TV (Fox11), filled as `local_or_team_focused`.
- ARI defensive play-caller: the only source (Cronkite News) did not explicitly state who calls the defensive plays, so the cell is blank.
- DEN offensive play-caller: filled from the team site (Webb), but agent 2 flagged that Payton was noncommittal; watch it for an in-season change.

## Agent reports, verbatim

### Teams 1-8 (finished 2026-10-05T21:28:27.362Z)

I have names for all 40 HC/OC/DC slots and all 8 offensive play-callers. Defensive play-callers are sourced for only 4 of 8 teams (BAL, BUF, CLE, ARI); the other 4 are blank. I found no in-season firing or play-calling handoff for any of the 8 teams, but my search for one was thin.

Caveat on the quotes: WebFetch returns text after a summarising model has processed it. Lines marked "(verbatim)" were given back as direct quotes. Lines marked "(summary)" are the tool's paraphrase, so check them against the page before relying on them.

All 40 role names are on 2026 pages, so none is stale. The "possibly stale" flags below apply only to older pages that came up about the Panthers' defensive play-calling.

| team | role | name | URL | quote | page date | notes |
|---|---|---|---|---|---|---|
| ARI | HC | Mike LaFleur | https://www.azcardinals.com/news/cardinals-retain-nick-rallis-as-defensive-coordinator-nathaniel-hackett | (verbatim LaFleur quote) "Nick is someone I have always great respect for…" — page names LaFleur head coach | 2026-02-13 | team site |
| ARI | OC | Nathaniel Hackett | same azcardinals URL; also https://africa.espn.com/nfl/story/_/id/47828748/source-cardinals-mike-lafleur-hires-nathaniel-hackett-oc | "With Nathaniel, when you combine his experience with his high level of offensive production…" | 2026-02-13 / 2026-02-04 | |
| ARI | DC | Nick Rallis | same azcardinals URL | Rallis "retained from Jonathan Gannon's staff" (summary) | 2026-02-13 | |
| ARI | Off play-caller | Mike LaFleur (HC) | https://africa.espn.com/nfl/story/_/id/47828748/... | "Mike LaFleur said Tuesday… he will be calling Arizona's offensive plays" (verbatim) | 2026-02-04 | Also https://abc7chicago.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ (ESPN content): "Playcaller: Mike LaFleur, head coach" (2026-09-03) |
| ARI | Def play-caller | BLANK (Rallis likely) | https://cronkitenews.azpbs.org/2026/09/15/mike-lafleur-cardinals-defense/ | LaFleur: "I thought Nick called a really good game." | 2026-09-15 | Cronkite News is not an approved source, so left blank |
| ATL | HC | Kevin Stefanski | https://atlantafalcons.com/news/atlanta-falcons-2026-coaching-staff | Stefanski "has been plenty busy in his short time with the team" | 2026-03-09 | joined 2026-01-17 |
| ATL | OC | Tommy Rees | same URL | lists OC Tommy Rees (summary) | 2026-03-09 | |
| ATL | DC | Jeff Ulbrich | https://www.espn.com/nfl/story/_/id/47661016/falcons-retaining-dc-jeff-ulbrich-head-coach-kevin-stefanski | Ulbrich "will remain in his position under new head coach Kevin Stefanski" (summary) | 2026-01-19 | new 3-year deal |
| ATL | Off play-caller | Tommy Rees (OC) | https://www.atlantafalcons.com/news/tommy-rees-offensive-play-caller-kevin-stefanski | Stefanski: "That's a setup that I'm very, very comfortable with" | 2026-01-28 | ABC/ESPN page: "Playcaller: Tommy Rees, offensive coordinator" (2026-09-03) |
| ATL | Def play-caller | BLANK | — | not sourced | — | no fetched page says who calls the defence in 2026 |
| BAL | HC | Jesse Minter | https://www.baltimoreravens.com/news/jesse-minter-ravens-defensive-play-caller-coordinators | page describes Minter as new head coach | 2026-01-29 | |
| BAL | OC | Declan Doyle | https://africa.espn.com/nfl/story/_/id/48958657/baltimore-ravens-2026-nfl-offensive-coordinator-declan-doyle-reboot-offense | names Doyle as OC, a "first-time playcaller" (summary) | 2026-06-06 | |
| BAL | DC | Anthony Weaver | same ESPN URL | names Weaver as DC (summary) | 2026-06-06 | Weaver is DC but does not call the defence (see next row) |
| BAL | Def play-caller | Jesse Minter (HC) | ravens URL above | "I do plan on calling the defense. I think that's a strength of mine" (verbatim) | 2026-01-29 | also https://www.espn.com/nfl/story/_/id/47976236/... : "Minter will call the plays on defense" |
| BAL | Off play-caller | Declan Doyle (OC) | https://abc7chicago.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ | "Playcaller: Declan Doyle, offensive coordinator" | 2026-09-03 | ESPN 47976236, Doyle: "the first time I was going to call plays…" |
| BUF | HC | Joe Brady | https://www.buffalobills.com/news/something-special-about-this-guy-why-pete-carmichael-waited-seven-years-to-get-back-with-joe-brady | Brady "will be the offensive play caller for the Bills" | 2026-02-05 | promoted from OC |
| BUF | OC | Pete Carmichael Jr. | same URL; https://www.nfl.com/news/bills-pete-carmichael-jr-new-offensive-coordinator | "Pete game plans to call the game," Brady said of his OC | 2026-02-05 | NFL.com page date not shown |
| BUF | DC | Jim Leonhard | https://www.buffalobills.com/news/how-the-bills-can-be-an-attacking-defense-under-new-defensive-coordinator-jim-leonhard | "Leonhard is also looking forward to calling plays for the first time as an NFL coach." | 2026-02-05 | |
| BUF | Off play-caller | Joe Brady (HC) | Carmichael URL above | "Brady made it clear from his first day on the job that he will be the offensive play caller for the Bills." | 2026-02-05 | ABC/ESPN agrees (2026-09-03) |
| BUF | Def play-caller | Jim Leonhard (DC) | Leonhard URL above | same quote as the DC row | 2026-02-05 | |
| CAR | HC | Dave Canales | https://www.panthers.com/news/panthers-announce-2026-coaching-staff | lists HC Canales (summary) | 2026-05-20 | |
| CAR | OC | Brad Idzik | same URL | lists OC Idzik (summary) | 2026-05-20 | |
| CAR | DC | Ejiro Evero | same URL; https://www.panthers.com/news/with-all-10-head-coaching-vacancies-filled-ejiro-evero-set-to-return-defensive-coordinator | Canales: "I have complete trust in Ejiro." | 2026-05-20 / 2026-02-01 | |
| CAR | Off play-caller | Brad Idzik (OC) | https://www.panthers.com/news/dave-canales-offensive-coordinator-brad-idzik-to-call-plays-in-2026 | "offensive coordinator Brad Idzik was going to call plays this year" | 2026-02-24 | Canales handed it over at the Combine; ABC/ESPN agrees (2026-09-03) |
| CAR | Def play-caller | BLANK | see notes | not sourced | — | See the blanks list below |
| CHI | HC | Ben Johnson | https://www.espn.com/nfl/story/_/id/47868016/source-bears-promoting-press-taylor-offensive-coordinator | "It's rare in Year 1 that you feel like you have a five-star staff…" | 2026-02-08 | |
| CHI | OC | Press Taylor | same ESPN URL | promoted from passing game coordinator, replacing Declan Doyle (summary) | 2026-02-08 | Doyle left for BAL |
| CHI | DC | Dennis Allen | https://chicago.suntimes.com/bears/2026/09/29/bears-eagles-dominant-best-development-dennis-allen-win-monday-night-tj-edwards | identifies Allen as DC; "Coach Ben Johnson gave Allen a game ball" | 2026-09-29 | |
| CHI | Off play-caller | Ben Johnson (HC) | https://abc7chicago.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ | "Playcaller: Ben Johnson, head coach" | 2026-09-03 | ESPN 2026-02-08 also says Johnson calls plays (summary) |
| CHI | Def play-caller | BLANK (Allen likely) | — | not sourced | — | See the blanks list below |
| CIN | HC | Zac Taylor | https://www.bengals.com/news/bengals-finalize-2026-coaching-staff | lists HC Taylor (summary) | 2026-02-13 | |
| CIN | OC | Dan Pitcher | same URL | lists OC Pitcher (summary) | 2026-02-13 | |
| CIN | DC | Al Golden | same URL | lists DC Golden (summary) | 2026-02-13 | |
| CIN | Off play-caller | Zac Taylor (HC) | https://abc7chicago.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ | "Playcaller: Zac Taylor, head coach" | 2026-09-03 | Pitcher called plays in the 2026 preseason, per a fantasy site (not approved, not fetched) |
| CIN | Def play-caller | BLANK | — | not sourced | — | no fetched page says it |
| CLE | HC | Todd Monken | https://www.espn.in/nfl/story/_/id/47948501/source-browns-hire-falcons-rutenberg-replace-schwartz-dc | Monken "does not anticipate changing Cleveland's defensive scheme" | 2026-02-16 | |
| CLE | OC | Travis Switzer | https://spectrumnews1.com/oh/columbus/news/2026/02/20/cleveland-browns-name-new-coordinators | Monken on Switzer: "He was our run game coordinator…" | 2026-02-20 | Spectrum News 1 (local TV) is not on the approved list. NBC/PFT "Browns announce OC Travis Switzer…" was seen in search but not fetched. |
| CLE | DC | Mike Rutenberg | https://www.clevelandbrowns.com/news/mike-rutenberg-keeps-relationships-at-the-core-of-leading-the-browns-defense | "As Rutenberg steps into his role as defensive coordinator for the Browns…" | 2026-03-05 | replaced Jim Schwartz |
| CLE | Off play-caller | Todd Monken (HC) | https://abc7chicago.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ | "Playcaller: Todd Monken, head coach" | 2026-09-03 | |
| CLE | Def play-caller | Mike Rutenberg (DC) | clevelandbrowns.com URL above | "he will also take on new responsibilities – including defensive playcalling." | 2026-03-05 | his first time calling plays |

**Blanks and why**
- **ARI defensive play-caller:** the only page that says it is Cronkite News (Sept 15, 2026), which is not an approved source. It quotes LaFleur saying "Nick called a really good game." A quote from azcardinals.com, ESPN or NFL.com would fill this as Rallis.
- **ATL defensive play-caller:** none of the pages I fetched says who calls the Falcons' defence in 2026.
- **CAR defensive play-caller:** there is a real conflict here.
  - Pages that name Evero as DC (Feb and May 2026) don't say who calls the defence.
  - EssentiallySports (Aug 7, 2026; not an approved source) says Jonathan Cooley called the defence in the preseason opener, and doesn't say whether that continues into the regular season.
  - The panthers.com piece saying Evero stays the regular-season caller is dated Sept 1, 2024. It is pre-2026 and possibly stale.
- **CHI defensive play-caller:** search snippets quote Xavier Woods saying Allen "called a heck of a game." The pages I fetched (Sun-Times Sept 29 and chicagobears.com Sept 30, 2026) only show Johnson saying "DA had a great plan," which doesn't establish who calls the plays.
- **CIN defensive play-caller:** no fetched page says it.

**Mid-season changes:** none found for these 8 teams through week 4.
- A general search turned up only offseason moves: Panthers HC Canales handed offensive play-calling to Idzik on Feb 24, 2026, and Ravens HC Minter said he will call the defence.
- I did not run a separate search for each team, so treat "none found" as unconfirmed.

**Other notes**
- Two sources were blocked: the AP article on the Cardinals' staff returned an error (429), and apnews.com, theathletic.com, cleveland.com and cincinnati.com can't be reached by the search tool.
- The ABC7 Chicago page is ESPN's "Who calls plays for every NFL team in 2026" piece (dated Sept 3, 2026). It lists offensive play-callers only.

### Teams 9-16 (finished 2026-10-05T21:28:49.232Z)

I found a source for 79 of the 80 values; the one blank is the Packers OC (Adam Stenavich, below). But not every source is on your approved list: about 10 cells rest only on local TV, Sports Illustrated's On SI team pages, Pro Football Network or Yahoo/Athlon, and 3 more on local TV backed only by a ranking. They are flagged "NL" in the notes and listed at the end so you can blank them. Most quotes are close summaries returned by the fetch tool, not exact copies; the ones in quotation marks come from fetches where I asked for exact wording.

No mid-season firing or play-calling handoff turned up for these 8 teams. The one live situation is Denver (see the Broncos rows).

Two pages cover several teams, so the table refers to them by short name:
- **ESPN-PC** = https://www.espn.com/nfl/story/_/id/49711157/nfl-playcallers-32-teams-mike-mcdaniel-sean-mcvay-mike-mccarthy (2026-09-03). It lists each team's offensive play-caller only; it has no defensive entries.
- **CBS-T10** = https://www.cbssports.com/nfl/news/top-10-offensive-and-defensive-play-callers/ (2026-08-05). It ranks the top 10 offensive and defensive play-callers entering 2026, plus "also receiving votes". It is a ranking, not a team announcement.

| team | role | name | URL | quote | page date | notes |
|---|---|---|---|---|---|---|
| DAL | HC | Brian Schottenheimer | ESPN-PC | Offensive play-caller listed as "Brian Schottenheimer, head coach" | 2026-09-03 | |
| DAL | OC | Klayton Adams | https://www.dallascowboys.com/news/2026-cowboys-coaching-tracker-arrivals-departures-and-latest-news | "report directly to offensive coordinator Klayton Adams" | 2026-02-16 | |
| DAL | DC | Christian Parker | same tracker page | Parker arrived "from the Philadelphia Eagles to take over as the team's new defensive coordinator" | 2026-02-16 | Hired Jan. 22, 2026, replacing the fired Matt Eberflus |
| DAL | Off. play-caller | Schottenheimer | ESPN-PC | "Brian Schottenheimer, head coach" (offensive play-caller list) | 2026-09-03 | |
| DAL | Def. play-caller | Parker (weak) | CBS-T10 | Parker is in the defensive play-callers' "also receiving votes" list | 2026-08-05 | Ranking only. A June 17, 2026 CBS article on Parker shortening play calls does not explicitly name him the caller |
| DEN | HC | Sean Payton | https://www.denverbroncos.com/news/broncos-announce-updates-to-2026-coaching-staff | Sean Payton listed as Head Coach | 2026-03-12 | |
| DEN | OC | Davis Webb | same page | Davis Webb listed as Offensive Coordinator | 2026-03-12 | Promoted after Joe Lombardi was fired |
| DEN | DC | Vance Joseph | same page | Vance Joseph listed as Defensive Coordinator | 2026-03-12 | |
| DEN | Off. play-caller | Davis Webb | https://www.denverbroncos.com/news/i-wouldn-t-do-it-if-i-didn-t-think-it-was-going-to-help-our-team-win-hc-sean-payton-announces-oc-davis-webb-to-call-plays-for-broncos-offense | "Recently promoted Offensive Coordinator Davis Webb will serve as the Broncos' play-caller" | 2026-02-24 | Still Webb as of 10-03 and 10-05 (see the Denver item after the table) |
| DEN | Def. play-caller | Vance Joseph (weak) | CBS-T10 | Ranked #8 defensive play-caller, "Vance Joseph, Broncos defensive coordinator" | 2026-08-05 | Ranking only |
| DET | HC | Dan Campbell | https://www.detroitlions.com/news/twentyman-5-takeaways-from-dc-kelvin-sheppard-moore-clark-rakestraw | "Head coach Dan Campbell, Sheppard and the defensive coaching staff did a deep dive" | 2026-08-02 | |
| DET | OC | Drew Petzing | https://www.espn.com/nfl/story/_/id/47662766/sources-lions-finalizing-deal-hire-drew-petzing-new-oc | "This should be a playcalling role in Detroit for Petzing" | 2026-01-19 | |
| DET | DC | Kelvin Sheppard | detroitlions.com, same page as HC | "Second-year defensive coordinator Kelvin Sheppard spoke to the media Sunday" | 2026-08-02 | |
| DET | Off. play-caller | Drew Petzing | ESPN-PC | "Drew Petzing, offensive coordinator" | 2026-09-03 | Campbell called plays from Week 10 of 2025 (ESPN, 2026-01-19) |
| DET | Def. play-caller | Kelvin Sheppard | https://www.si.com/nfl/lions/onsi/how-kelvin-sheppard-can-improve-in-2026 | Campbell on Sheppard: "you kind of key and diagnose yourself as a play-caller" | 2026-07-16 | NL (On SI) |
| GB | HC | Matt LaFleur | https://www.packers.com/news/packers-name-jonathan-gannon-defensive-coordinator-feb-2-2026 | Head Coach Matt LaFleur announced the hire | 2026-02-02 | |
| GB | OC | Adam Stenavich | https://fox11online.com/sports/packers-and-nfl/packers-announce-2026-coaching-staff | "Adam Stenavich: Offensive coordinator" | 2026-03-19 (upd. 03-23) | NL (local TV); see blanks |
| GB | DC | Jonathan Gannon | packers.com, same page as HC | "The Green Bay Packers have named Jonathan Gannon defensive coordinator." | 2026-02-02 | Replaced Jeff Hafley |
| GB | Off. play-caller | Matt LaFleur | ESPN-PC | "Matt LaFleur, head coach" | 2026-09-03 | |
| GB | Def. play-caller | Jonathan Gannon | https://www.tmj4.com/sports/new-packers-coordinators-speak-for-the-first-time-as-offseason-continues | "he plans to call plays from the sideline" | 2026-05-04 | NL (Milwaukee TV) |
| HOU | HC | DeMeco Ryans | https://www.houstontexans.com/news/texans-vs-cowboys-week-4-preview-demeco-ryans | Refers to "HC DeMeco Ryans" | 2026-10-02 | Texans are 0-4 |
| HOU | OC | Nick Caley | https://www.espn.com/nfl/story/_/id/47684076/texans-oc-nick-caley-expected-return-gm-says | "I would anticipate Nick being here next year." (GM Caserio) | 2026-01-21 | |
| HOU | DC | Matt Burke | https://www.krgv.com/news/texans-coordinators-preview-new-schemes-as-training-camp-continues | Names Matt Burke as Defensive Coordinator | 2026-07-31 | NL (local TV) |
| HOU | Off. play-caller | Nick Caley | ESPN-PC | "Nick Caley, offensive coordinator" | 2026-09-03 | |
| HOU | Def. play-caller | Matt Burke (weak) | CBS-T10 | Ranked #10, "Matt Burke, Texans defensive coordinator" | 2026-08-05 | Ranking only. Burke took over defensive calls from Ryans mid-2025 (search snippets only, not fetched) |
| IND | HC | Shane Steichen | https://www.colts.com/news/colts-announce-2026-coaching-staff-marian-hobby-defensive-line-lou-anarumo | Head Coach: Shane Steichen | 2026-02-23 | |
| IND | OC | Jim Bob Cooter | same page | Offensive Coordinator: Jim Bob Cooter | 2026-02-23 | |
| IND | DC | Lou Anarumo | same page | Defensive Coordinator: Lou Anarumo | 2026-02-23 | |
| IND | Off. play-caller | Shane Steichen | ESPN-PC | "Steichen enters his fourth season as head coach and has established himself as one of the more respected playcallers" | 2026-09-03 | |
| IND | Def. play-caller | Lou Anarumo (weak) | CBS-T10 | Anarumo (Colts) in the defensive "also receiving votes" list | 2026-08-05 | Ranking only |
| JAX | HC | Liam Coen | https://www.jaguars.com/news/k000589-coen-campanile-udinski-return-2026-huge | Names Coen head coach; Coen: "It's huge" | 2026-02-26 | |
| JAX | OC | Grant Udinski | same page | Udinski named as returning OC | 2026-02-26 | |
| JAX | DC | Anthony Campanile | same page | Campanile named as returning DC | 2026-02-26 | |
| JAX | Off. play-caller | Liam Coen | ESPN-PC | "Liam Coen, head coach" | 2026-09-03 | Udinski called most preseason plays (PFT, 2026-07-31). The 2025 CBS "Coen will call plays" page is stale |
| JAX | Def. play-caller | Anthony Campanile (weak) | CBS-T10 | Ranked #9, "Anthony Campanile, Jaguars defensive coordinator" | 2026-08-05 | Ranking only |
| KC | HC | Andy Reid | https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/chiefs-finalize-deal-with-eric-bieniemy-to-return-as-their-oc | "Chiefs head coach Andy Reid, though, will continue as the team's play caller." | 2026-01-21 | |
| KC | OC | Eric Bieniemy | https://www.chiefs.com/news/chiefs-name-eric-bieniemy-as-offensive-coordinator | "Eric Bieniemy officially signed on as Offensive Coordinator heading into the 2026 season" | 2026-01-23 | Replaced Matt Nagy |
| KC | DC | Steve Spagnuolo | https://www.kctv5.com/2026/07/30/spagnuolo-hoping-find-same-ingredient-success-with-sneeds-return-chiefs-secondary/ | "Kansas City Chiefs defensive coordinator Steve Spagnuolo has a new-look secondary on his hands in 2026." | 2026-07-30 | NL (local TV); CBS-T10 also names him Chiefs DC |
| KC | Off. play-caller | Andy Reid | PFT (same as HC row) + ESPN-PC | "will continue as the team's play caller"; ESPN: "Reid's 28th consecutive season as his team's offensive playcaller" | 2026-01-21 / 09-03 | KCTV5 (2026-01-26) quotes Reid: "I still enjoy calling plays." |
| KC | Def. play-caller | Steve Spagnuolo (weak) | CBS-T10 | Ranked #2, "Steve Spagnuolo, Chiefs defensive coordinator" | 2026-08-05 | Ranking only |

**Denver, the only live in-season situation:** Webb is still calling plays, but Payton has not committed to keeping him there.
- Yahoo/Athlon Sports (NL), Oct. 3: Webb is still the play-caller, and the offense ranks 26th in EPA per play after three games. https://sports.yahoo.com/articles/broncos-offense-ranks-no-26-140500926.html
- Pro Football Network (NL), Oct. 5, after the 24-14 Week 4 loss to the 49ers: Payton said "each game we look at everything." https://www.profootballnetwork.com/broncos-loss-reaction-49ers-week-4-2026/
- No handoff has been announced. Check again before Week 5.

**Blanks and weak spots**
1. **GB OC (Adam Stenavich) is the one blank.** Every page I fetched that names him is on neither list: Fox11 (local TV), plus search snippets from Acme Packing Company (a fan site), packers.com and NFL.com, which I didn't open. A packers.com page about Stenavich's promotion exists, but it may be from the 2025 offseason. Fetch it before you rely on him.
2. **Five defensive play-callers rest only on CBS-T10:** DAL Parker, DEN Joseph, HOU Burke, IND Anarumo, JAX Campanile. Spagnuolo (KC) did too, but the CBS ranking backs a local-TV source there. CBS ranks them as play-callers, but none of their teams said "will call plays" on any page I fetched. If you want a team statement, treat all six as "not sourced".
3. **Sources not on your list (NL):**
   - KC DC: KCTV5
   - HOU DC: KRGV
   - GB DC play-caller: TMJ4
   - DET DC play-caller: SI On SI
   - DEN in-season status: Pro Football Network and Yahoo/Athlon
   - GB OC: Fox11 (see blank 1)
4. **Unverified search snippets I did not use:**
   - A claim that Petzing would call plays, attributed to Lions GM Brad Holmes (snippet traced to Audacy, not fetched).
   - A claim that Lions GM Brad Holmes said Petzing "will call plays"; the fetched NFL.com piece didn't contain that.
   - Claims that Schottenheimer sits in on Parker's defensive game planning (Yardbarker, a sports aggregator).
5. **Pages that failed to load:** Houston Chronicle (Week 4 game story), 9News Denver, denversports.com, AP via the Washington Times, and acmepackingcompany.com.
6. **Mid-season check covered general searches only.** I searched for 2026 in-season firings and handoffs for all 8 teams and found none, but I did not check each team's news feed day by day.

### Teams 17-24 (finished 2026-10-05T21:27:42.326Z)

I found all 40 values, with two caveats. Every defensive play-caller except the Giants' is sourced, though three of them (LAC, NE, NO) rest on weaker sourcing, explained in the notes. The Giants' defensive play-caller stays blank. The fetched pages show no mid-season 2026 firing or play-calling handoff for any of the 8 teams.

**Caveat on quotes:** WebFetch returns text through a summarizing model. I asked for exact wording each time, but re-check any quote before it goes into a fixture.

### Table

Source keys, used in the URL column:
- **ESPN-PC**: https://abc7ny.com/post/calls-plays-every-nfl-team-2026-what-know/19783946/ ("Who calls plays for every NFL team in 2026?", ESPN NFL Nation syndicated on ABC7, 2026-09-03). It covers offensive play-callers only.
- **CBS-PC**: https://www.cbssports.com/nfl/news/top-10-offensive-and-defensive-play-callers/ (Zachary Pereles, 2026-08-05). It is a ranking of play-callers "entering the 2026 season", so a team appears only if its play-caller got votes.

| team | role | name | URL | quote | page date | notes |
|---|---|---|---|---|---|---|
| LA | HC | Sean McVay | https://www.therams.com/news/rams-2026-coaching-staff-set | "Sean McVay enters his 10th year as head coach of the Rams." | 2026-02-23 | |
| LA | OC | Nate Scheelhaase | same | "Offensive Coordinator: Nate Scheelhaase" | 2026-02-23 | Dave Ragone (QB coach) has "associate coordinator" added to his title |
| LA | DC | Chris Shula | same | "Chris Shula returns for his third season as defensive coordinator" | 2026-02-23 | |
| LA | Off. play-caller | Sean McVay | ESPN-PC | "Playcaller: Sean McVay, head coach" | 2026-09-03 | Scheelhaase called the plays in the preseason opener (fantasynerds search result only, not fetched) |
| LA | Def. play-caller | Chris Shula | CBS-PC | "7. Chris Shula, Rams defensive coordinator" (defensive play-callers list) | 2026-08-05 | |
| LAC | HC | Jim Harbaugh | https://www.chargers.com/news/mike-mcdaniel-chris-oleary-new-coordinator-2026 | "Jim Harbaugh hired former Miami Dolphins head coach McDaniel." | 2026-07-24 | One search listed Harbaugh on a Week 4 "hot seat" list. That is not a change. |
| LAC | OC | Mike McDaniel | https://www.clickondetroit.com/sports/2026/01/26/mike-mcdaniel-joins-harbaugh-herbert-as-chargers-offensive-coordinator-after-dolphins-firing/ | "Mike McDaniel has agreed to become the Los Angeles Chargers' offensive coordinator." | 2026-01-26 (AP, Greg Beacham) | |
| LAC | DC | Chris O'Leary | chargers.com (above) | "The Chargers on Wednesday agreed to terms with Chris O'Leary to become their Defensive Coordinator." | 2026-07-24 | |
| LAC | Off. play-caller | Mike McDaniel | ESPN-PC | "Playcaller: Mike McDaniel, offensive coordinator" | 2026-09-03 | ClutchPoints (2026-09-01) agrees: "Harbaugh tabbed him to call plays" |
| LAC | Def. play-caller | Chris O'Leary | chargers.com (above) | "hired Mike McDaniel and Chris O'Leary ... one of the nine teams with new playcallers on both offense and defense" | 2026-07-24 | Weaker: the page links him to "new playcallers" but doesn't say he calls the plays |
| LV | HC | Klint Kubiak | ESPN-PC | "Playcaller: Klint Kubiak, head coach" | 2026-09-03 | |
| LV | OC | Andrew Janocko | https://ktnv.com/sports/las-vegas-raiders-promote-rob-leonard-to-defensive-coordinator-may-have-found-oc-too | "Andrew Janocko will follow Kubiak from Seattle to be the offensive coordinator." | 2026-02-15 | KTNV is the Las Vegas ABC TV station, not a newspaper. The AP versions would not load (402/429/404). |
| LV | DC | Rob Leonard | same | "Rob Leonard was officially elevated to defensive coordinator on Sunday." | 2026-02-15 | |
| LV | Off. play-caller | Klint Kubiak | ESPN-PC | "Playcaller: Klint Kubiak, head coach" | 2026-09-03 | Conflict: Kubiak on KTNV (2026-02-15): "I've never called the game by myself. That's something we do as a coaching staff together." |
| LV | Def. play-caller | Rob Leonard | https://www.raiders.com/news/inside-rob-leonard-s-successful-debut-as-raiders-defensive-coordinator | "Rob Leonard wanted to keep things simple in his first game as the Raiders' defensive play-caller." | 2026-09-18 | |
| MIA | HC | Jeff Hafley | https://www.news4jax.com/sports/2026/01/19/jeff-hafley-reaches-agreement-with-miami-dolphins-to-become-their-coach-ap-source-says/ | "The Miami Dolphins hired former Packers defensive coordinator Jeff Hafley as their coach on Monday" | 2026-01-19 (AP, Rob Maaddi) | |
| MIA | OC | Bobby Slowik | https://www.cbssports.com/fantasy/football/news/dolphins-2026-fantasy-football-outlook-offensive-coordinator-bobby-slowik/ | "Bobby Slowik was promoted from passing game coordinator to offensive coordinator under new head coach Jeff Hafley." | 2026-06-09 | |
| MIA | DC | Sean Duggan | https://africa.espn.com/nfl/story/_/id/47800410/sources-dolphins-hiring-sean-duggan-defensive-coordinator | "The Miami Dolphins are hiring former Green Bay Packers linebackers coach Sean Duggan as their defensive coordinator." | 2026-02-01 (Marcel Louis-Jacques) | |
| MIA | Off. play-caller | Bobby Slowik | ESPN-PC | "Playcaller: Bobby Slowik, offensive coordinator" | 2026-09-03 | |
| MIA | Def. play-caller | Jeff Hafley | ESPN Duggan article (above) | Hafley: "It's something that I love to do. It really connects me with that group" | 2026-02-01 | Per the page, he said this in January about calling the defensive plays himself. CBS-PC also lists "Jeff Hafley, Dolphins coach" under defensive play-callers receiving votes. |
| MIN | HC | Kevin O'Connell | ESPN-PC | "O'Connell has called the Vikings' plays in every season since he arrived as head coach in 2022." | 2026-09-03 | |
| MIN | OC | Wes Phillips | https://www.vikings.com/news/2026-coaching-staff-updates-promotions-hires | "Wes Phillips \| Offensive Coordinator" | 2026-02-24 | |
| MIN | DC | Brian Flores | same | "Brian Flores \| Defensive Coordinator" | 2026-02-24 | |
| MIN | Off. play-caller | Kevin O'Connell | ESPN-PC | "Playcaller: Kevin O'Connell, head coach" | 2026-09-03 | |
| MIN | Def. play-caller | Brian Flores | CBS-PC | "5. Brian Flores, Vikings defensive coordinator" (defensive play-callers list) | 2026-08-05 | |
| NE | HC | Mike Vrabel | https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/patriots-name-terrell-williams-assistant-head-coach-as-they-finalize-2026-staff | Page names Vrabel as head coach (summarizer gave no clean verbatim line) | 2026-03-16 (PFT) | Also: Williams "moved into a higher-ranking role on Mike Vrabel's staff" (NFP, 2026-02-17) |
| NE | OC | Josh McDaniels | same | "Offensive coordinator Josh McDaniels will work with ..." | 2026-03-16 | |
| NE | DC | Zak Kuhr | https://www.nationalfootballpost.com/reports-patriots-elevate-zak-kuhr-to-defensive-coordinator | "The New England Patriots are promoting Zak Kuhr from inside linebackers coach to defensive coordinator" | 2026-02-17 | NFP is not on your source list. PFT's "Zak Kuhr moving up to the defensive coordinator role" (2026-03-16) covers this too. |
| NE | Off. play-caller | Josh McDaniels | ESPN-PC | "Playcaller: Josh McDaniels, offensive coordinator" | 2026-09-03 | |
| NE | Def. play-caller | Zak Kuhr | CBS-PC | "Zak Kuhr, Patriots defensive coordinator" (defensive list, also receiving votes) | 2026-08-05 | Weaker: only a ranking vote. NFP says he was the play-caller from Week 2 of 2025. |
| NO | HC | Kellen Moore | ESPN-PC | "Playcaller: Kellen Moore, head coach" | 2026-09-03 | |
| NO | OC | Doug Nussmeier | https://www.neworleanssaints.com/video/doug-nussmeier-offensive-coordinator-interview-9-1-2026 | "New Orleans Saints offensive coordinator Doug Nussmeier speaks with the media ... September 1, 2026." | 2026-09-01 | |
| NO | DC | Brandon Staley | https://www.neworleanssaints.com/team/coaches-roster/brandon-staley | "Brandon Staley is in his second season as defensive coordinator for the Saints in 2026." | no date shown (bio text says 2026) | |
| NO | Off. play-caller | Kellen Moore | ESPN-PC | "This is Moore's second year calling plays as a head coach" | 2026-09-03 | |
| NO | Def. play-caller | Brandon Staley | CBS-PC | "Brandon Staley, Saints defensive coordinator" (defensive list, also receiving votes) | 2026-08-05 | Weaker: only a ranking vote |
| NYG | HC | John Harbaugh | https://www.giants.com/news/john-harbaugh-announces-2026-coaching-staff-coordinators-matt-nagy-dennard-wilson-chris-horton | "John Harbaugh has announced his inaugural staff as head coach of the New York Football Giants." | 2026-02-18 | |
| NYG | OC | Matt Nagy | same | "His coordinators are Matt Nagy (offense), Dennard Wilson (defense) and Chris Horton (special teams)." | 2026-02-18 | |
| NYG | DC | Dennard Wilson | same | same quote | 2026-02-18 | |
| NYG | Off. play-caller | Matt Nagy | ESPN-PC | "Playcaller: Matt Nagy, offensive coordinator" | 2026-09-03 | |
| NYG | Def. play-caller | (blank) | — | not sourced | — | see below |

### Blanks and weak spots
- **NYG defensive play-caller is blank.** Three Giants pages were fetched: the staff announcement (2026-02-18), "Cover 3" (2026-06-05) and the Wilson defense feature (2026-04-09). None says who calls the defense, and Wilson is not in the CBS ranking. A BigBlueView piece titled "...Dennard Wilson brings an aggressive play calling style" returned 403, and it may be about his Titans years anyway.
- **LAC, NE and NO defensive play-callers rest on weaker sourcing.** LAC rests only on chargers.com's "new playcallers on both offense and defense" line, which names both hires but doesn't say O'Leary calls the plays. NE and NO rest only on "also receiving votes" entries in the CBS ranking. If you want only explicit statements, blank these three.
- **The LV offensive play-caller is in conflict.** ESPN lists Kubiak as the play-caller, but in February Kubiak said the staff calls the game "together".
- **Some quotes are not exact.** The NE head coach row has no exact quote. The Hafley quote is his own words, with the play-calling context taken from the article.
- **Several hire articles would not load** (the AP mirrors for the Raiders, Rams and Dolphins hires), so other outlets' pages are used instead.

### Mid-season 2026 changes
None found for these 8 teams. Two other searches came up, and neither affects the table:
- Results about Raiders OCs Chip Kelly and Luke Getsy being fired describe earlier seasons, not 2026.
- A Week 4 debate over Broncos play-calling (Payton and Webb) is about Denver, which is not on the list. A search snippet also said Titans coach Brian Callahan was fired "Oct. 13". That date is after today and I never fetched the page, so treat it as unreliable.

### Teams 25-32 (finished 2026-10-05T21:28:27.362Z)

No head coach, coordinator or play-caller changes turned up for any of the 8 teams through Week 4, but four slots stay blank. Those are the Eagles and Seahawks defensive play-callers, Tampa Bay's defensive coordinator, and the 49ers offensive coordinator from a source on your list.

Two limits on the evidence:
- **Quotes aren't exact copies.** The fetch tool returns pages through a summarizing model. I asked for word-for-word text, but a quote can still be slightly off, so spot-check any value you put in a fixture.
- **Some sites wouldn't load.** apnews.com, nytimes.com/The Athletic, newsday.com and nypost.com refused the connection. jetsxfactor.com, behindthesteelcurtain.com, nfl.com's amp page and some AP mirror sites failed to load (blocked, rate-limited or broken). Where I fall back on a source that isn't on your list, the notes say so.

## Table

| Team | Role | Name | URL | Quote | Page date | Notes |
|---|---|---|---|---|---|---|
| NYJ | HC | Aaron Glenn | https://www.newyorkjets.com/news/2026-combine-aaron-glenn-will-call-defensive-plays-this-season-02-24-2026 | Glenn: "I will be the playcaller. To me, play-calling is my superpower." | 2026-02-24 | Team site |
| NYJ | OC | Frank Reich | https://www.clickondetroit.com/sports/2026/02/04/jets-hire-veteran-coach-frank-reich-as-offensive-coordinator/ | "Reich was hired Wednesday by Glenn as the Jets' offensive coordinator" | 2026-02-04 | AP story, reprinted on a TV-station site |
| NYJ | DC | Brian Duker | https://www.newyorkjets.com/news/2026-combine-aaron-glenn-will-call-defensive-plays-this-season-02-24-2026 | "Brian had been with me for three years. He knows exactly how I want to operate." | 2026-02-24 | The tool reported Duker as DC from this page, but the quote doesn't say "coordinator" |
| NYJ | Off. play-caller | Frank Reich | https://www.espn.com/nfl/story/_/id/49711157/nfl-playcallers-32-teams-mike-mcdaniel-sean-mcvay-mike-mccarthy | "Playcaller: Frank Reich, offensive coordinator" | 2026-09-03 | ESPN's league-wide playcaller list. The quote is the tool's rendering of the entry |
| NYJ | Def. play-caller | Aaron Glenn | (newyorkjets.com, above) | "I will be the playcaller." | 2026-02-24 | |
| PHI | HC | Nick Sirianni | https://www.nbcsportsphiladelphia.com/nfl/philadelphia-eagles/sean-mannion-call-plays-coaches-booth-sideline-offensive-coordinator-jalen-hurts-nick-sirianni/750540/ | "Mannion had conversations with Nick Sirianni, Vic Fangio and other staff members" | 2026-09-11 | Shows Sirianni on staff but doesn't say "head coach". The July 20 NBCSP article also names him as HC |
| PHI | OC | Sean Mannion | https://www.nbcsportsphiladelphia.com/nfl/philadelphia-eagles/nick-sirianni-not-concerned-sean-mannion-inexperienced-offensive-coordinator/742483/ | "Not only is Mannion a first-time offensive coordinator, but he's also a first-time play caller." | 2026-07-20 | |
| PHI | DC | Vic Fangio | https://www.inquirer.com/eagles/defensive-coordinator-vic-fangio-will-return-2026-20260204.html | "The 67-year-old defensive coordinator will return for his third season at the helm of the Eagles defense" | 2026-02-04 | An Inquirer article dated 2026-09-30 still calls him DC |
| PHI | Off. play-caller | Sean Mannion | (NBCSP 09-11, above) | "Sean Mannion has decided where he'll be calling plays from this season." | 2026-09-11 | ESPN's 09-03 list agrees |
| PHI | Def. play-caller | BLANK | (NBCSP 09-11) | "...that's where Fangio is for every game." | 2026-09-11 | Only implied (he sits in the booth). No page says he calls defensive plays |
| PIT | HC | Mike McCarthy | https://www.steelers.com/news/steelers-complete-2026-coaching-staff | "The Steelers finalized Head Coach Mike McCarthy's 2026 coaching staff today." | 2026-02-12 | |
| PIT | OC | Brian Angelichio | (same) | "Offensive Coordinator: Brian Angelichio" | 2026-02-12 | |
| PIT | DC | Patrick Graham | (same) | "The Steelers named Patrick Graham the team's defensive coordinator." | 2026-02-12 | ESPN (2026-01-30) agrees |
| PIT | Off. play-caller | Mike McCarthy | https://africa.espn.com/nfl/story/_/id/47781532/steelers-hire-patrick-graham-mike-mccarthy-d-coordinator | "McCarthy said Tuesday he planned to call plays" | 2026-01-30 | ESPN's 09-03 list agrees ("Mike McCarthy, head coach") |
| PIT | Def. play-caller | Patrick Graham | https://www.steelers.com/news/why-graham-prefers-a-bird-s-eye-view | "Patrick Graham ... prefers calling plays from the coaches' box rather than the sideline." | 2026-08-22 | |
| SEA | HC | Mike Macdonald | https://www.seahawks.com/news/seattle-seahawks-finalize-2026-coaching-staff | "Mike Macdonald (Head Coach)" | 2026-03-12 | |
| SEA | OC | Brian Fleury | (same) | "Brian Fleury (Offensive Coordinator)" | 2026-03-12 | Replaced Klint Kubiak |
| SEA | DC | Aden Durde | (same) | "Aden Durde (Defensive Coordinator)" | 2026-03-12 | |
| SEA | Off. play-caller | Brian Fleury | https://www.heraldnet.com/2026/08/05/seahawks-oc-brian-fleury-challenged-by-macdonalds-defense/ | "...his new offensive coordinator and play caller, Brian Fleury." | 2026-08-05 | ESPN's 09-03 list agrees |
| SEA | Def. play-caller | BLANK | https://www.yakimaherald.com/... (Durde article) | "Seahawks coach Mike Macdonald could become the first head coach to win a Super Bowl while calling the defensive plays" | 2026-02-04 | Covers the 2025 season, not 2026. Search snippets suggest he still calls them, but no page I opened says so for 2026 |
| SF | HC | Kyle Shanahan | https://www.49ers.com/team/coaches-roster/ | "Kyle Shanahan – Head Coach" | undated (fetched 2026-10-05) | sfstandard (2026-10-04) confirms he is still coaching (4-0 start) |
| SF | OC | Klay Kubiak | https://www.49ers.com/team/coaches-roster/ | "Klay Kubiak – Offensive Coordinator" | undated; bio covers 2025 | Possibly stale. The only 2026-dated confirmation is fantasynerds (2026-08-11, citing The Athletic), which is not on your list |
| SF | DC | Raheem Morris | https://abc7news.com/18522925 | "The San Francisco 49ers are hiring Raheem Morris as their new defensive coordinator" | 2026-02-01 | Replaced Robert Saleh |
| SF | Off. play-caller | Kyle Shanahan | ESPN 09-03 (above) | "Playcaller: Kyle Shanahan, head coach" | 2026-09-03 | Kubiak called plays in the 2025 preseason (PFT, 2025-08-06), which is not a 2026 change |
| SF | Def. play-caller | Raheem Morris | https://sfstandard.com/2026/05/07/raheem-morris-49ers-defense-romello-height/ | "After Robert Saleh's departure, Raheem Morris is charged with calling the plays." | 2026-05-07 | San Francisco Standard: local news site, not a newspaper on your list |
| TB | HC | Todd Bowles | https://www.buccaneers.com/team/coaches-roster/index | "Todd Bowles enters his fifth season as head coach of the Tampa Bay Buccaneers" | undated (2026 page) | |
| TB | OC | Zac Robinson | (same) | "Zac Robinson enters his first season as offensive coordinator with the Buccaneers in 2026." | 2026 | Replaced the fired Josh Grizzard (Jan 2026) |
| TB | DC | BLANK / none listed | (same) | No DC appears on the staff page | | Bowles runs the defense himself |
| TB | Off. play-caller | Zac Robinson | ESPN 09-03 (above) | "Playcaller: Zac Robinson, offensive coordinator" | 2026-09-03 | |
| TB | Def. play-caller | Todd Bowles | https://www.tampabay.com/sports/bucs/2026/02/25/how-help-2026-bucs-defense-head-coach-not-worried-about-offense/ | "Todd Bowles, who is also the defensive play-caller, says the hiring of OC Zac Robinson will help him refocus." | 2026-02-25 | |
| TEN | HC | Robert Saleh | https://www.tennesseetitans.com/news/titans-hire-brian-daboll-as-offensive-coordinator | "It's a key hire for new head coach Robert Saleh." | 2026-01-27 | |
| TEN | OC | Brian Daboll | (same) | "Brian Daboll has been hired as offensive coordinator." | 2026-01-27 | |
| TEN | DC | Gus Bradley | https://www.wsmv.com/2026/02/18/titans-coordinators-speak-new-role-with-tennessee/ | "Bradley was named defensive coordinator." | 2026-02-18 | Nashville TV station |
| TEN | Off. play-caller | Brian Daboll | https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/robert-saleh-will-call-the-titans-defensive-plays | "...a former head coach calling offensive plays in Brian Daboll" | 2026-01-29 | ESPN's 09-03 list agrees |
| TEN | Def. play-caller | Robert Saleh | https://www.wsmv.com/2026/02/18/titans-coordinators-speak-new-role-with-tennessee/ | "Saleh will call defensive plays, the same arrangement he and Bradley had in San Francisco." | 2026-02-18 | PFT (2026-01-29) agrees |
| WAS | HC | Dan Quinn | https://www.thebanner.com/sports/commanders-nfl/commanders-coordinators-growing-pains-M46ZN3NTXVCZ5H6ILJC2S6KAHY/ | "This is how Quinn is handling his young play-callers in his critical third season leading Washington." | 2026-09-20 | Baltimore Banner: not on your list |
| WAS | OC | David Blough | https://www.29news.com/2026/02/11/commanders-try-reversing-last-seasons-dismal-results-with-two-first-time-coordinators/ | Tool summary: Blough is OC (first-time coordinator, age 30) | 2026-02-11 | AP story on a TV-station site. I didn't get an exact sentence |
| WAS | DC | Daronte Jones | https://amp.nfl.com/news/commanders-hiring-vikings-db-coach-daronte-jones-as-defensive-coordinator | "...hiring Minnesota Vikings defensive backs coach Daronte Jones as their new defensive coordinator" | 2026-01-26 | |
| WAS | Off. play-caller | David Blough | ESPN 09-03 (above) | "Playcaller: David Blough, offensive coordinator" | 2026-09-03 | The Banner (09-20) agrees |
| WAS | Def. play-caller | Daronte Jones | (Banner, above) | "...hired two first-time play-callers this offseason in Blough and defensive coordinator Daronte Jones" | 2026-09-20 | Earlier sources disagree, see below |

## Blanks and why
- **PHI defensive play-caller:** No page says Fangio calls the defense in 2026. NBC Sports Philadelphia (2026-09-11) only says he sits in the booth "for every game".
- **SEA defensive play-caller:** The only explicit statement (Yakima Herald, 2026-02-04) is about the 2025 Super Bowl run. Search snippets said he called plays in the regular season and Durde called them in the preseason, but no page I opened said that for 2026.
- **TB defensive coordinator:** The official staff page lists no DC, and Bowles is confirmed as defensive play-caller. If your data needs a DC value, it should be "none", not a guess.
- **SF offensive coordinator:** Kubiak is filled from the 49ers' staff page, but that page is undated and his bio covers 2025. The only 2026-dated confirmation is a fantasy aggregator citing The Athletic, which I couldn't open.

## Conflicts and stale items
- **WAS defensive play-caller:** NFL.com (2026-01-26) said "it will remain to be seen if Quinn maintains play-calling duties". An SI piece (2025-12-04) said Quinn might keep them. The latest source, the Banner (2026-09-20), names Jones as a play-caller.
- **Background 2025 changes, not 2026:**
  - Quinn took over Washington's defensive calls from Joe Whitt Jr. midway through 2025.
  - Kubiak called the 49ers' plays in the 2025 preseason.

## Mid-season 2026 changes
I found none for these 8 teams through Week 4 (as of 2026-10-05).
- **Titans:** 0-4. Bleacher Report (2026-09-29, not on your list) puts Daboll on the hot seat, but nothing reports a firing.
- **Misleading search snippet:** One search summary claimed "Saleh was fired, Mike McCoy interim". The page it came from (2026 Titans Wikipedia) shows no firing; the snippet mixed in the 2025 Callahan firing.
- **49ers:** Shanahan had a serious car accident in July 2026 (sfstandard, 2026-10-04), but a search snippet says he went back to calling plays by Week 1.
