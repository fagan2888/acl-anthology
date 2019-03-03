# Marcel Bollmann <marcel@bollmann.me>, 2019

import re
from . import data
from .papers import Paper
from .venues import VenueIndex
from .sigs import SIGIndex
from .utils import format_markup_element


class Volume:
    def __init__(
        self, front_matter: Paper, venue_index: VenueIndex, sig_index: SIGIndex
    ):
        """Instantiate a proceedings volume.

        `venue_index` and `sig_index` are used to find venues and SIGs
        associated with this proceedings volume.
        """
        self.front_matter_id = front_matter.paper_id
        self.top_level_id = front_matter.top_level_id
        self.attrib = front_matter.attrib.copy()
        if "author" in self.attrib:
            # Authors of the front matter are the volume's editors
            self.attrib["editor"] = self.attrib["author"]
            del self.attrib["author"]
        # Some fields should not be copied from the front matter
        for attrib in ("revision", "erratum", "pages"):
            if attrib in self.attrib:
                del self.attrib[attrib]
        self.attrib["url"] = data.ANTHOLOGY_URL.format(self.full_id)
        self.attrib["venues"] = venue_index.register(self)
        self.attrib["sigs"] = sig_index.get_associated_sigs(front_matter.full_id)
        self._set_meta_info()
        self.content = []
        if self.top_level_id[0] not in ("J", "Q"):
            # J and Q don't have front matter, but others do
            self.append(front_matter)

    def _set_meta_info(self):
        """Derive journal title, volume, and issue no. used in metadata.

        This function replicates functionality that was previously hardcoded in
        'app/helpers/papers_helper.rb' of the Rails app."""
        self.attrib["meta_journal_title"] = data.get_journal_title(
            self.top_level_id, self.attrib["title"]
        )
        volume_no = re.search(
            r"Volume\s*(\d+)", self.attrib["title"], flags=re.IGNORECASE
        )
        if volume_no is not None:
            self.attrib["meta_volume"] = volume_no.group(1)
        issue_no = re.search(
            r"(Number|Issue)\s*(\d+-?\d*)", self.attrib["title"], flags=re.IGNORECASE
        )
        if issue_no is not None:
            self.attrib["meta_issue"] = issue_no.group(2)

    @property
    def full_id(self):
        if self.top_level_id[0] == "W":
            # If volume is a workshop, use the first two digits of ID, e.g. W15-01
            _id = "{}-{}".format(self.top_level_id, self.front_matter_id[:2])
        else:
            # If not, only use the first digit, e.g. Q15-1
            _id = "{}-{}".format(self.top_level_id, self.front_matter_id[0])
        return _id

    @property
    def paper_ids(self):
        return [paper.full_id for paper in self.content]

    def append(self, paper):
        self.content.append(paper)
        if paper.parent_volume_id is not None:
            log.error(
                "Trying to append paper '{}' to volume '{}', but it already belongs to '{}'".format(
                    paper.full_id, self.full_id, paper.parent_volume_id
                )
            )
        paper.parent_volume_id = self.full_id

    def get(self, name, default=None):
        try:
            return self.attrib[name]
        except KeyError:
            return default

    def get_title(self, form="xml"):
        """Returns the paper title, optionally formatting it.

        Accepted formats:
          - xml:   Include any contained XML tags unchanged
          - plain: Strip all XML tags, returning only plain text
          - html:  Convert XML tags into valid HTML tags
        """
        return format_markup_element(self.get("xml_title"), form)
