import type { Metadata } from "next";
import { Contact, LegalPage } from "@/components/LegalPage";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = {
  title: "Legal notice",
};

export default function LegalNoticePage() {
  return (
    <LegalPage title="Legal notice">
      <h2>Operator</h2>
      <p>
        {OPERATOR.name}
        {OPERATOR.country ? (
          <>
            <br />
            {OPERATOR.country}
          </>
        ) : null}
      </p>
      <p>
        Contact: <Contact />
      </p>

      <h2>About this site</h2>
      <p>
        ListForge is a private, non-commercial portfolio project. Nothing is sold through this
        site.
      </p>

      <h2>Brands and data</h2>
      <p>
        This project is not affiliated with, authorised or endorsed by Foxelli Group or any brand
        named on this site. Brand names appear only to show how per-brand settings drive the
        output. Brand voices were inferred from public storefronts and are not official
        guidelines. The example products were written for this demo and are not company data.
        No brand logos, images or published product text are used.
      </p>

      <h2>Hosting</h2>
      <p>
        The website is hosted by Vercel Inc. The server behind the tool is hosted by OVHcloud in
        the European Union. Generated text is produced by a model run by Groq, Inc.
      </p>
    </LegalPage>
  );
}
