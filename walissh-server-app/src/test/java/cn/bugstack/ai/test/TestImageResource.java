package cn.bugstack.ai.test;

import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/** Loads the image fixture from a text-only Base64 resource. */
public final class TestImageResource {

    private TestImageResource() {
    }

    public static Resource dog() throws IOException {
        Resource encoded = new ClassPathResource("dog.png.base64");
        String base64 = new String(encoded.getContentAsByteArray(), StandardCharsets.US_ASCII);
        return new ByteArrayResource(Base64.getMimeDecoder().decode(base64));
    }
}
