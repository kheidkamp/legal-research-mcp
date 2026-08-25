# Test Evidence - 0.3.3-dev

Local regression result: **39/39 PASS**.

New coverage includes:

- label-based discovery of the BFH decision-search form when the old canonical input name is absent;
- replay of actual live form field names;
- preservation of Extbase `__trustedProperties` state;
- no injection of stale canonical `Aktenzeichen` fields into alternate live forms;
- unchanged pre-2010 fail-closed case gate;
- unchanged official-document retrieval regression suite.

Live BFH validation remains required because the build environment cannot reproduce the production BFH edge/application response end-to-end.
