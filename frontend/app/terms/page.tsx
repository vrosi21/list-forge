import type { Metadata } from "next";
import { Contact, LegalPage } from "@/components/LegalPage";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = {
  title: "Terms",
};

export default function TermsPage() {
  return (
    <LegalPage title="Terms of use">
      <p>
        These terms apply to this website and the ListForge tool. By using them you accept these
        terms. If you do not accept them, please do not use the site.
      </p>

      <h2>What this is</h2>
      <p>
        ListForge is a portfolio project by {OPERATOR.name}. It is offered free of charge to
        demonstrate how generated product copy can be checked before it is used. It is not a
        commercial service.
      </p>

      <h2>Access codes</h2>
      <p>
        The tool is open to invited reviewers. Each access code is given to one person and should
        not be shared. Codes have a daily limit on runs, and the operator may change those limits
        or withdraw a code at any time.
      </p>

      <h2>Acceptable use</h2>
      <ul>
        <li>Upload product data only. Do not upload personal, confidential or unlawful content.</li>
        <li>Do not try to get around access codes, limits or other protections.</li>
        <li>Do not overload, scan or attack the service, or use it through automated scripts.</li>
      </ul>

      <h2>Generated text</h2>
      <p>
        Text is written by a language model and may be wrong, even when every check passes. The
        checks catch many unsupported claims but not all of them. Review any text yourself before
        you use it anywhere. You are responsible for how you use it.
      </p>

      <h2>Your content</h2>
      <p>
        You keep any rights you have in the product data you upload. You allow the operator to
        store and process it to run the tool, show you the results and reuse them for later runs.
      </p>

      <h2>Brand names</h2>
      <p>
        Brand names appear only to show how per-brand settings change the output. They belong to
        their owners. This project is not affiliated with, authorised or endorsed by Foxelli
        Group or any brand named on the site.
      </p>

      <h2>No warranty</h2>
      <p>
        The site is provided as it is, without any promise that it will be available, accurate
        or fit for a particular purpose. It may change or be taken offline at any time.
      </p>

      <h2>Liability</h2>
      <p>
        As far as the law allows, the operator is not liable for any loss arising from use of the
        site or of generated text. Nothing in these terms limits liability that cannot be limited
        by law.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these terms can be sent through <Contact />.
      </p>
    </LegalPage>
  );
}
