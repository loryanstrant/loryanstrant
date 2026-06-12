## What I prompted:

While SharePoint has the ability to limit version counts, that doesn't always fix the problem.
All it takes is a few wayward files to completely blow out the storage quota of a site.

Some file types do not handle incremental versioning, such as PowerPoint. This especially problematic with autosave in desktop apps. For example: you open a PowerPoint presentation with videos and large images that is 250MB and you update the presenters name, it is now 500MB. Update the presentation date, it's now 750MB. Update the client's name or presentation title, you're now up to 1GB.
I've seen PowerPoint presentations that were only a few hundred MB in size, take up tens of gigabytes due to the amount of versions, especially when multiple people are collaborating.

The driveItemVersion endpoint only has documentation for List items, and Get item, and while there is no Delete item documented - it is possible.
https://learn.microsoft.com/en-us/graph/api/resources/driveitemversion?view=graph-rest-1.0

HTTP method: DELETE
https://graph.microsoft.com/v1.0/drives/<SharePoint library ID>/items/<SharePoint drive item ID>/versions/<version number>

Have only tested it using application permissions (not delegated).


I recently used this method to purge 3TB of file versions in only 8 minutes.

Have not validated if this works if retention policies are enabled.


## What it wrote:

### Using Microsoft Graph to Bulk Delete SharePoint Version History
SharePoint versioning is one of those features that sounds entirely reasonable until it quietly devours your storage quota. The ability to limit version counts helps — in theory. In practice, all it takes is a handful of problem files to blow out a site's allocation completely.

The most common offender? PowerPoint.

**Why PowerPoint is the villain here**

Unlike many file types, PowerPoint doesn't handle incremental versioning gracefully. Every save creates a new version at roughly the same size as the original file. Pair that with autosave in desktop apps and a file with embedded videos and high-resolution images, and the maths gets ugly fast.

To make it concrete: you open a 250MB presentation and update the presenter's name. That's 500MB. You change the date — 750MB. You swap out the client name — you're at 1GB. For a single file that, in its current state, is still only 250MB.

I've seen PowerPoint files of a few hundred megabytes ballooning to tens of gigabytes purely from version accumulation, especially when multiple collaborators are working across the same file simultaneously. Version limits help, but they're reactive — they don't address what's already sitting there.

**Enter the driveItemVersion endpoint**

The Microsoft Graph API has a driveItemVersion resource, and the documentation covers listing versions and getting a specific item. What the documentation does not cover — but what does work — is deleting a specific version.

The endpoint:

DELETE https://graph.microsoft.com/v1.0/drives/<SharePoint library ID>/items/<SharePoint drive item ID>/versions/<version number>
I've only tested this with application permissions, not delegated. Worth noting upfront, as is the fact that I haven't validated behaviour when retention policies are in place — if you're in a regulated environment, test carefully before running anything at scale.

**What "at scale" looks like in practice**

I recently used this method to purge 3TB of file versions across a SharePoint environment. Total time: eight minutes.

That's not a typo. Three terabytes, eight minutes. The Graph API handles the heavy lifting efficiently once you have the right flow in place, and the approach scales well because you're not waiting on the SharePoint UI or doing anything through a browser.

The general approach using Power Automate:

Identify libraries and files — get the list of document libraries across the target sites using the SharePoint or Graph connector, then enumerate the files within each library.
Retrieve versions — for each file, call the driveItemVersion list endpoint to get all versions associated with that item.
Filter to versions you want to remove — typically anything beyond the N most recent, or versions older than a defined date, or all versions for files above a certain size threshold.
Call DELETE for each version — iterate through the filtered list and issue a DELETE request per version. This is where an HTTP action in Power Automate with application authentication does the work.
The SharePoint library ID and drive item ID are both retrievable via Graph — the library ID comes from the drive endpoint for the site, and the item ID from listing items within that drive.

**What this won't fix**

Version limits configured in SharePoint library settings will prevent future accumulation, but they don't reach back and clean up what's already there. If you've inherited a tenant where version settings were never configured, or where they were set generously and then tightened, you likely have a historical backlog that limits alone won't resolve.

That's the gap this approach fills. Run the purge to clear the backlog, set your version limits going forward, and the problem stays manageable.

It's also worth auditing which libraries contain the largest files before assuming the issue is widespread. In my experience, the storage blowout tends to be concentrated in a relatively small number of sites and libraries — often ones used by specific teams for client-facing material or large media files. Targeting those first gives you the biggest return for the effort.

**A note on the documentation gap**

The absence of the DELETE method from the driveItemVersion documentation is mildly frustrating. It works, it's consistent with Graph API conventions, and given that listing and getting versions are both documented, omitting delete feels like an oversight rather than a deliberate restriction.

If you're tracking changes to the Graph API — and if you're building workflows against it, you should be — the Graph changelog is the authoritative source. The RSS feed is often more current than the page itself, which is a whole separate conversation.

The short version: don't assume that because something isn't in the documentation it can't be done. Test it in a non-production environment with application permissions, validate the behaviour, and then scale with confidence.
