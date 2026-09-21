import type { Metadata } from "next";
import { Contact, LegalPage } from "@/components/LegalPage";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacy",
};

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy notice">
      <p>
        This notice explains what information this site handles, why, and what you can ask for.
        ListForge is a non-commercial portfolio project. It runs no analytics, shows no
        advertising and sets no cookies.
      </p>

      <h2>Who is responsible</h2>
      <p>
        The site is run by {OPERATOR.name}
        {OPERATOR.country ? `, ${OPERATOR.country}` : ""}. You can reach the operator through{" "}
        <Contact />.
      </p>

      <h2>Visiting the site</h2>
      <p>
        The website is hosted by Vercel Inc. in the United States. To deliver pages and protect
        the service, Vercel records technical data about each request, such as your IP address,
        the time, the page requested and your browser type. This site does not add any tracking
        of its own.
      </p>

      <h2>Storage in your browser</h2>
      <p>
        Two values are kept in your browser&apos;s local storage: your access code, if you enter
        one, and your choice of light or dark mode. The theme choice never leaves your browser.
        The access code is sent to the server only with requests that check access or run the
        tool. Clearing this site&apos;s data in your browser removes both. These values are
        needed for the features you ask for, so no consent banner is shown.
      </p>

      <h2>Using the tool</h2>
      <p>
        The tool talks to a server run by the operator at OVHcloud in the European Union. When
        you use it, the following is processed:
      </p>
      <ul>
        <li>
          Request logs with your IP address, the time and the request made. They are used to find
          faults and abuse, and they are rotated automatically, so older entries are overwritten
          after a short period.
        </li>
        <li>
          Your IP address, held in memory only, to limit how many requests one address can make.
          It is not written to disk.
        </li>
        <li>
          Your access code, to check that you were invited and to count the runs you use each
          day. Runs are logged against the name the operator gave that code.
        </li>
        <li>
          The product rows you upload or type, and the text generated from them. They are stored
          in a database on the server so results can be shown and reused. They are kept until the
          operator deletes them, and you can ask for that at any time.
        </li>
      </ul>

      <h2>The language model</h2>
      <p>
        To generate text, each product row is sent to Groq, Inc. in the United States, which runs
        the model. Groq processes the rows under its own terms. Product rows should describe
        products, not people, so please do not put personal or confidential data in them.
      </p>

      <h2>Why this is allowed</h2>
      <p>
        The processing described here rests on the operator&apos;s legitimate interest in running
        a working demonstration, keeping it secure and limiting its costs. Where data goes to
        providers in the United States, it relies on the safeguards those providers offer for
        such transfers, such as standard contractual clauses.
      </p>

      <h2>Your rights</h2>
      <p>
        You can ask for a copy of the data held about you, for its correction or deletion, for
        its processing to be restricted, or object to its processing. Contact the operator
        through <Contact />. You can also complain to the data protection authority where you
        live.
      </p>

      <h2>Decisions about you</h2>
      <p>
        The tool makes automatic decisions about generated text only. It makes no decisions
        about people.
      </p>

      <h2>Changes</h2>
      <p>
        If this notice changes, the new version will be posted here with a new date at the top.
      </p>
    </LegalPage>
  );
}
