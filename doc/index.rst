EVE-SRP: An EVE Online Ship Replacement Program App
===================================================

EVE-SRP is designed to facilitate a ship replacement (SRP) or reimbursement
program in the game EVE Online. It features a pluggable authentication setup so
it can integrate with existing authentication systems, and comes with built in
support for TEST Alliance's Auth and Brave's Core systems. It also features a
configurable killmail source system, with built in support for zKillboard based
killboards and the recent CREST killmail endpoint. Again, this is an extensible
system so if you have a custom killboard, as long as there's some sort of
programmatic access, you can probably write a custom adaptor.

For the users, EVE-SRP offers quick submissision and an easy way to check your
SRP pending requsts. On the administrative side, EVE-SRP uses the concept of
divisions, with different users and groups of users being able to submit
requests, review them (set payouts and approve or reject requests), and finally
pay out approved requests. This separation allows spreading of the labor
intensive and low risk task of evaluating requests from the high privilege of
paying out requests from a central wallet. This also means different groups can
have different reviewing+paying teams. For example, you may wish for capital
losses to be reviewed by a special team that is aware of your capital group's
fitting requirements, and in lieu of payouts you may have someone hand out
replacement hulls.

.. toctree::
   :maxdepth: 2

   authentication



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

