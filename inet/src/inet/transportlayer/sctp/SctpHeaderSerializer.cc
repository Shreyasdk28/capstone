//
// Copyright (C) 2005 Christian Dankbar, Irene Ruengeler, Michael Tuexen, Andras Varga
// Copyright (C) 2010 Thomas Dreibholz
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


#include "inet/transportlayer/sctp/SctpHeaderSerializer.h"

#include "inet/common/checksum/Checksum.h"
#include "inet/common/Endian.h"
#include "inet/common/packet/serializer/ChunkSerializerRegistry.h"
#include "inet/networklayer/common/IpProtocolId_m.h"
#include "inet/networklayer/ipv4/Ipv4HeaderSerializer.h"
#include "inet/networklayer/ipv4/Ipv4Header_m.h"
#include "inet/transportlayer/contract/sctp/SctpCommand_m.h"
#include "inet/transportlayer/sctp/SctpAssociation.h"
#include "inet/transportlayer/sctp/headers/sctphdr.h"

#if !defined(_WIN32) && !defined(__CYGWIN__) && !defined(_WIN64)
#include <arpa/inet.h>
#include <netinet/in.h> // htonl, ntohl, ...
#include <sys/socket.h>
#endif // if !defined(_WIN32) && !defined(__CYGWIN__) && !defined(_WIN64)

#include <sys/types.h>
#define MAXBUFLEN    1 << 16

namespace inet {

namespace sctp {

Register_Serializer(SctpHeader, SctpHeaderSerializer);

int SctpHeaderSerializer::getKeysHandle()
{
    static int keysHandle = cSimulationOrSharedDataManager::registerSharedVariableName("inet::sctp::SctpHeaderSerializer::keys");
    return keysHandle;
}

void SctpHeaderSerializer::serialize(MemoryOutputStream& stream, const Ptr<const Chunk>& chunk) const
{
    uint8_t buffer[MAXBUFLEN];
    memset(&buffer, 0, MAXBUFLEN);
//    int32_t size_chunk = sizeof(struct chunk);

    int authstart = 0;
    const auto& msg = staticPtrCast<const SctpHeader>(chunk);
    struct common_header *ch = (struct common_header *)(buffer);
    uint32_t writtenbytes = sizeof(struct common_header);

    // fill SCTP common header structure
    ch->source_port = htons(msg->getSrcPort());
    ch->destination_port = htons(msg->getDestPort());
    ch->verification_tag = htonl(msg->getVTag());
    ch->checksum = htonl(0);

    // SCTP chunks:
    int32_t noChunks = msg->getSctpChunksArraySize();
    for (int32_t cc = 0; cc < noChunks; cc++) {
        SctpChunk *chunk = const_cast<SctpChunk *>(check_and_cast<const SctpChunk *>((msg)->getSctpChunks(cc)));
        unsigned char chunkType = chunk->getSctpChunkType();
        switch (chunkType) {
            case DATA: {
                EV_INFO << simTime() << " SctpAssociation:: Data sent \n";
                SctpDataChunk *dataChunk = check_and_cast<SctpDataChunk *>(chunk);
                struct data_chunk *dc = (struct data_chunk *)(buffer + writtenbytes); // append data to buffer
                unsigned char flags = 0;

                // fill buffer with data from SCTP data chunk structure
                dc->type = dataChunk->getSctpChunkType();
                if (dataChunk->getUBit())
                    flags |= UNORDERED_BIT;
                if (dataChunk->getBBit())
                    flags |= BEGIN_BIT;
                if (dataChunk->getEBit())
                    flags |= END_BIT;
                if (dataChunk->getIBit())
                    flags |= I_BIT;
                dc->flags = flags;
                dc->length = htons(dataChunk->getByteLength());
                dc->tsn = htonl(dataChunk->getTsn());
                dc->sid = htons(dataChunk->getSid());
                dc->ssn = htons(dataChunk->getSsn());
                dc->ppi = htonl(dataChunk->getPpid());
                writtenbytes += SCTP_DATA_CHUNK_LENGTH;
                SctpSimpleMessage *smsg = check_and_cast<SctpSimpleMessage *>(dataChunk->getEncapsulatedPacket());
                const uint32_t datalen = smsg->getDataLen();
                if (smsg->getDataArraySize() >= datalen) {
                    for (uint32_t i = 0; i < datalen; i++) {
                        dc->user_data[i] = smsg->getData(i);
                    }
                }
                writtenbytes += ADD_PADDING(datalen);
                break;
            }

            case INIT: {
                EV_INFO << "serialize INIT size=" << (unsigned long)msg->getChunkLength().get<B>() << "\n";

                // source data from internal struct:
                SctpInitChunk *initChunk = check_and_cast<SctpInitChunk *>(chunk);
                // destination is send buffer:
                struct init_chunk *ic = (struct init_chunk *)(buffer + writtenbytes); // append data to buffer
                uint16_t padding_last = 0;

                // fill buffer with data from Sctp init chunk structure
                ic->type = initChunk->getSctpChunkType();
                ic->flags = 0; // no flags available in this type of SctpChunk
                ic->initiate_tag = htonl(initChunk->getInitTag());
                ic->a_rwnd = htonl(initChunk->getA_rwnd());
                ic->mos = htons(initChunk->getNoOutStreams());
                ic->mis = htons(initChunk->getNoInStreams());
                ic->initial_tsn = htonl(initChunk->getInitTsn());
                int32_t parPtr = 0;
                // Var.-Len. Parameters
                if (initChunk->getIpv4Supported() || initChunk->getIpv6Supported()) {
                    struct supported_address_types_parameter *sup_addr = (struct supported_address_types_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    sup_addr->type = htons(INIT_SUPPORTED_ADDRESS);
                    sup_addr->length = htons(8);
                    if (initChunk->getIpv4Supported() && initChunk->getIpv6Supported()) {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV4);
                        sup_addr->address_type_2 = htons(INIT_PARAM_IPV6);
                    }
                    else if (initChunk->getIpv4Supported()) {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV4);
                        sup_addr->address_type_2 = 0;
                    }
                    else {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV6);
                        sup_addr->address_type_2 = 0;
                    }
                    parPtr += 8;
                }
                if (initChunk->getForwardTsn() == true) {
                    struct forward_tsn_supported_parameter *forward = (struct forward_tsn_supported_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    forward->type = htons(FORWARD_TSN_SUPPORTED_PARAMETER);
                    forward->length = htons(4);
                    parPtr += 4;
                }
                int32_t numaddr = initChunk->getAddressesArraySize();
                for (int32_t i = 0; i < numaddr; i++) {
#ifdef INET_WITH_IPv4
                    if (initChunk->getAddresses(i).getType() == L3Address::IPv4) {
                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                        ipv4addr->type = htons(INIT_PARAM_IPV4);
                        ipv4addr->length = htons(8);
                        ipv4addr->address = htonl(initChunk->getAddresses(i).toIpv4().getInt());
                        parPtr += sizeof(struct init_ipv4_address_parameter);
                    }
#endif // ifdef INET_WITH_IPv4
#ifdef INET_WITH_IPv6
                    if (initChunk->getAddresses(i).getType() == L3Address::IPv6) {
                        struct init_ipv6_address_parameter *ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                        ipv6addr->type = htons(INIT_PARAM_IPV6);
                        ipv6addr->length = htons(20);
                        for (int32_t j = 0; j < 4; j++) {
                            ipv6addr->address[j] = htonl(initChunk->getAddresses(i).toIpv6().words()[j]);
                        }
                        parPtr += sizeof(struct init_ipv6_address_parameter);
                    }
#endif // ifdef INET_WITH_IPv6
                }
                int chunkcount = initChunk->getSepChunksArraySize();
                if (chunkcount > 0) {
                    struct supported_extensions_parameter *supext = (struct supported_extensions_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    supext->type = htons(SUPPORTED_EXTENSIONS);
                    int chunkcount = initChunk->getSepChunksArraySize();
                    supext->length = htons(sizeof(struct supported_extensions_parameter) + chunkcount);
                    for (int i = 0; i < chunkcount; i++) {
                        supext->chunk_type[i] = initChunk->getSepChunks(i);
                    }
                    parPtr += sizeof(struct supported_extensions_parameter) + chunkcount;
                    padding_last = ADD_PADDING(sizeof(struct supported_extensions_parameter) + chunkcount) - (sizeof(struct supported_extensions_parameter) + chunkcount);
                }
                if (initChunk->getHmacTypesArraySize() > 0) {
                    if (padding_last > 0) {
                        parPtr += padding_last;
                        padding_last = 0;
                    }
                    struct random_parameter *random = (struct random_parameter *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    random->type = htons(RANDOM);
                    unsigned char *vector = (unsigned char *)malloc(64);
                    struct random_parameter *rp = (struct random_parameter *)((unsigned char *)vector);
                    rp->type = htons(RANDOM);
                    int randomsize = initChunk->getRandomArraySize();
                    for (int i = 0; i < randomsize; i++) {
                        random->random[i] = (initChunk->getRandom(i));
                        rp->random[i] = (initChunk->getRandom(i));
                    }
                    parPtr += ADD_PADDING(sizeof(struct random_parameter) + randomsize);
                    random->length = htons(sizeof(struct random_parameter) + randomsize);
                    rp->length = htons(sizeof(struct random_parameter) + randomsize);
                    keys.sizeKeyVector = sizeof(struct random_parameter) + randomsize;
                    struct tlv *chunks = (struct tlv *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    struct tlv *cp = (struct tlv *)(((unsigned char *)vector) + keys.sizeKeyVector);

                    chunks->type = htons(CHUNKS);
                    cp->type = htons(CHUNKS);
                    int chunksize = initChunk->getSctpChunkTypesArraySize();
                    EV_DETAIL << "chunksize=" << chunksize << "\n";
                    for (int i = 0; i < chunksize; i++) {
                        chunks->value[i] = (initChunk->getSctpChunkTypes(i));
                        EV_DETAIL << "chunkType=" << initChunk->getSctpChunkTypes(i) << "\n";
                        cp->value[i] = (initChunk->getSctpChunkTypes(i));
                    }
                    chunks->length = htons(sizeof(struct tlv) + chunksize);
                    cp->length = htons(sizeof(struct tlv) + chunksize);
                    keys.sizeKeyVector += sizeof(struct tlv) + chunksize;
                    parPtr += ADD_PADDING(sizeof(struct tlv) + chunksize);
                    struct hmac_algo *hmac = (struct hmac_algo *)(((unsigned char *)ic) + sizeof(struct init_chunk) + parPtr);
                    struct hmac_algo *hp = (struct hmac_algo *)(((unsigned char *)vector) + keys.sizeKeyVector);
                    hmac->type = htons(HMAC_ALGO);
                    hp->type = htons(HMAC_ALGO);
                    hmac->length = htons(4 + 2 * initChunk->getHmacTypesArraySize());
                    hp->length = htons(4 + 2 * initChunk->getHmacTypesArraySize());
                    keys.sizeKeyVector += (4 + 2 * initChunk->getHmacTypesArraySize());
                    for (unsigned int i = 0; i < initChunk->getHmacTypesArraySize(); i++) {
                        hmac->ident[i] = htons(initChunk->getHmacTypes(i));
                        hp->ident[i] = htons(initChunk->getHmacTypes(i));
                    }
                    parPtr += ADD_PADDING(4 + 2 * initChunk->getHmacTypesArraySize());
                    padding_last = ADD_PADDING(4 + 2 * initChunk->getHmacTypesArraySize()) - (4 + 2 * initChunk->getHmacTypesArraySize());
                    parPtr -= padding_last;

                    for (unsigned int k = 0; k < keys.sizeKeyVector; k++) {
                        keys.keyVector[k] = vector[k];
                    }
                    free(vector);
                }

                ic->length = htons(SCTP_INIT_CHUNK_LENGTH + parPtr);
                writtenbytes += SCTP_INIT_CHUNK_LENGTH + parPtr + padding_last;
                break;
            }

            case INIT_ACK: {
                SctpInitAckChunk *initAckChunk = check_and_cast<SctpInitAckChunk *>(chunk);
                // destination is send buffer:
                struct init_ack_chunk *iac = (struct init_ack_chunk *)(buffer + writtenbytes); // append data to buffer
                // fill buffer with data from Sctp init ack chunk structure
                iac->type = initAckChunk->getSctpChunkType();
                iac->flags = 0; // no flags available in this type of SctpChunk
                iac->initiate_tag = htonl(initAckChunk->getInitTag());
                iac->a_rwnd = htonl(initAckChunk->getA_rwnd());
                iac->mos = htons(initAckChunk->getNoOutStreams());
                iac->mis = htons(initAckChunk->getNoInStreams());
                iac->initial_tsn = htonl(initAckChunk->getInitTsn());
                // Var.-Len. Parameters
                int32_t parPtr = 0;
                if (initAckChunk->getIpv4Supported() || initAckChunk->getIpv6Supported()) {
                    struct supported_address_types_parameter *sup_addr = (struct supported_address_types_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    sup_addr->type = htons(INIT_SUPPORTED_ADDRESS);
                    sup_addr->length = htons(8);
                    if (initAckChunk->getIpv4Supported() && initAckChunk->getIpv6Supported()) {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV4);
                        sup_addr->address_type_2 = htons(INIT_PARAM_IPV6);
                    }
                    else if (initAckChunk->getIpv4Supported()) {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV4);
                        sup_addr->address_type_2 = 0;
                    }
                    else {
                        sup_addr->address_type_1 = htons(INIT_PARAM_IPV6);
                        sup_addr->address_type_2 = 0;
                    }
                    parPtr += 8;
                }
                if (initAckChunk->getForwardTsn() == true) {
                    struct forward_tsn_supported_parameter *forward = (struct forward_tsn_supported_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    forward->type = htons(FORWARD_TSN_SUPPORTED_PARAMETER);
                    forward->length = htons(4);
                    parPtr += 4;
                }

                int32_t numaddr = initAckChunk->getAddressesArraySize();
                for (int32_t i = 0; i < numaddr; i++) {
#ifdef INET_WITH_IPv4
                    if (initAckChunk->getAddresses(i).getType() == L3Address::IPv4) {
                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                        ipv4addr->type = htons(INIT_PARAM_IPV4);
                        ipv4addr->length = htons(8);
                        ipv4addr->address = htonl(initAckChunk->getAddresses(i).toIpv4().getInt());
                        parPtr += sizeof(struct init_ipv4_address_parameter);
                    }
#endif // ifdef INET_WITH_IPv4
#ifdef INET_WITH_IPv6
                    if (initAckChunk->getAddresses(i).getType() == L3Address::IPv6) {
                        struct init_ipv6_address_parameter *ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                        ipv6addr->type = htons(INIT_PARAM_IPV6);
                        ipv6addr->length = htons(20);
                        for (int j = 0; j < 4; j++) {
                            ipv6addr->address[j] = htonl(initAckChunk->getAddresses(i).toIpv6().words()[j]);
                        }
                        parPtr += sizeof(struct init_ipv6_address_parameter);
                    }
#endif // ifdef INET_WITH_IPv6
                }
                int chunkcount = initAckChunk->getSepChunksArraySize();
                if (chunkcount > 0) {
                    struct supported_extensions_parameter *supext = (struct supported_extensions_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    supext->type = htons(SUPPORTED_EXTENSIONS);
                    int chunkcount = initAckChunk->getSepChunksArraySize();
                    supext->length = htons(sizeof(struct supported_extensions_parameter) + chunkcount);
                    for (int i = 0; i < chunkcount; i++) {
                        supext->chunk_type[i] = initAckChunk->getSepChunks(i);
                    }
                    parPtr += ADD_PADDING(sizeof(struct supported_extensions_parameter) + chunkcount);
                }
                uint32_t uLen = initAckChunk->getUnrecognizedParametersArraySize();
                if (uLen > 0) {
                    int32_t k = 0;
                    uint32_t pLen = 0;
                    while (uLen > 0) {
                        struct tlv *unknown = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                        unknown->type = htons(UNRECOGNIZED_PARAMETER);
                        pLen = initAckChunk->getUnrecognizedParameters(k + 2) * 16 + initAckChunk->getUnrecognizedParameters(k + 3);
                        unknown->length = htons(pLen + 4);
                        for (uint32_t i = 0; i < ADD_PADDING(pLen); i++, k++)
                            unknown->value[i] = initAckChunk->getUnrecognizedParameters(k);
                        parPtr += ADD_PADDING(pLen + 4);
                        uLen -= ADD_PADDING(pLen);
                    }
                }
                if (initAckChunk->getHmacTypesArraySize() > 0) {
                    unsigned int sizeVector;
                    struct random_parameter *random = (struct random_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    random->type = htons(RANDOM);
                    int randomsize = initAckChunk->getRandomArraySize();
                    unsigned char *vector = (unsigned char *)malloc(64);
                    struct random_parameter *rp = (struct random_parameter *)((unsigned char *)vector);
                    rp->type = htons(RANDOM);
                    for (int i = 0; i < randomsize; i++) {
                        random->random[i] = (initAckChunk->getRandom(i));
                        rp->random[i] = (initAckChunk->getRandom(i));
                    }
                    parPtr += ADD_PADDING(sizeof(struct random_parameter) + randomsize);
                    random->length = htons(sizeof(struct random_parameter) + randomsize);
                    rp->length = htons(sizeof(struct random_parameter) + randomsize);
                    sizeVector = ntohs(rp->length);
                    struct tlv *chunks = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    struct tlv *cp = (struct tlv *)(((unsigned char *)vector) + 36);
                    chunks->type = htons(CHUNKS);
                    cp->type = htons(CHUNKS);
                    int chunksize = initAckChunk->getSctpChunkTypesArraySize();
                    for (int i = 0; i < chunksize; i++) {
                        chunks->value[i] = (initAckChunk->getSctpChunkTypes(i));
                        cp->value[i] = (initAckChunk->getSctpChunkTypes(i));
                    }
                    chunks->length = htons(sizeof(struct tlv) + chunksize);
                    cp->length = htons(sizeof(struct tlv) + chunksize);
                    sizeVector += sizeof(struct tlv) + chunksize;
                    parPtr += ADD_PADDING(sizeof(struct tlv) + chunksize);
                    struct hmac_algo *hmac = (struct hmac_algo *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    struct hmac_algo *hp = (struct hmac_algo *)(((unsigned char *)(vector)) + 36 + sizeof(struct tlv) + chunksize);
                    hmac->type = htons(HMAC_ALGO);
                    hp->type = htons(HMAC_ALGO);
                    hmac->length = htons(4 + 2 * initAckChunk->getHmacTypesArraySize());
                    hp->length = htons(4 + 2 * initAckChunk->getHmacTypesArraySize());
                    sizeVector += (4 + 2 * initAckChunk->getHmacTypesArraySize());
                    for (unsigned int i = 0; i < initAckChunk->getHmacTypesArraySize(); i++) {
                        hmac->ident[i] = htons(initAckChunk->getHmacTypes(i));
                        hp->ident[i] = htons(initAckChunk->getHmacTypes(i));
                    }
                    parPtr += ADD_PADDING(4 + 2 * initAckChunk->getHmacTypesArraySize());
                    for (unsigned int k = 0; k < min(sizeVector, 64); k++) {
                        if (keys.sizeKeyVector != 0)
                            keys.peerKeyVector[k] = vector[k];
                        else
                            keys.keyVector[k] = vector[k];
                    }

                    if (keys.sizeKeyVector != 0)
                        keys.sizePeerKeyVector = sizeVector;
                    else
                        keys.sizeKeyVector = sizeVector;
                    /* ToDo */
//                    calculateSharedKey();
                    free(vector);
                }
                int32_t cookielen = initAckChunk->getCookieArraySize();
                if (cookielen == 0) {
                    SctpCookie *stateCookie = (SctpCookie *)(initAckChunk->getStateCookie());
//                    SctpCookie *stateCookie = check_and_cast<SctpCookie *>(initAckChunk->getStateCookie());
                    struct init_cookie_parameter *cookie = (struct init_cookie_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    cookie->type = htons(INIT_PARAM_COOKIE);
                    cookie->length = htons(SCTP_COOKIE_LENGTH + 4);
                    cookie->creationTime = htonl((uint32_t)stateCookie->getCreationTime().dbl());
                    cookie->localTag = htonl(stateCookie->getLocalTag());
                    cookie->peerTag = htonl(stateCookie->getPeerTag());
                    for (int32_t i = 0; i < 32; i++) {
                        cookie->localTieTag[i] = stateCookie->getLocalTieTag(i);
                        cookie->peerTieTag[i] = stateCookie->getPeerTieTag(i);
                    }
                    parPtr += (SCTP_COOKIE_LENGTH + 4);
                }
                else {
                    struct tlv *cookie = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parPtr);
                    cookie->type = htons(INIT_PARAM_COOKIE);
                    cookie->length = htons(cookielen + 4);
                    for (int32_t i = 0; i < cookielen; i++)
                        cookie->value[i] = initAckChunk->getCookie(i);
                    parPtr += cookielen + 4;
                }
                iac->length = htons(SCTP_INIT_CHUNK_LENGTH + parPtr);
                writtenbytes += SCTP_INIT_CHUNK_LENGTH + parPtr;
                break;
            }

            case SACK: {
                SctpSackChunk *sackChunk = check_and_cast<SctpSackChunk *>(chunk);

                // destination is send buffer:
                struct sack_chunk *sac = (struct sack_chunk *)(buffer + writtenbytes); // append data to buffer
                writtenbytes += sackChunk->getByteLength();

                // fill buffer with data from Sctp init ack chunk structure
                sac->type = sackChunk->getSctpChunkType();
                sac->flags = 0;
                sac->length = htons(sackChunk->getByteLength());
                uint32_t cumtsnack = sackChunk->getCumTsnAck();
                sac->cum_tsn_ack = htonl(cumtsnack);
                sac->a_rwnd = htonl(sackChunk->getA_rwnd());
                sac->nr_of_gaps = htons(sackChunk->getNumGaps());
                sac->nr_of_dups = htons(sackChunk->getNumDupTsns());

                // GAPs and Dup. TSNs:
                int16_t numgaps = sackChunk->getNumGaps();
                int16_t numdups = sackChunk->getNumDupTsns();
                for (int16_t i = 0; i < numgaps; i++) {
                    struct sack_gap *gap = (struct sack_gap *)(((unsigned char *)sac) + sizeof(struct sack_chunk) + i * sizeof(struct sack_gap));
                    gap->start = htons(sackChunk->getGapStart(i) - cumtsnack);
                    gap->stop = htons(sackChunk->getGapStop(i) - cumtsnack);
                }
                for (int16_t i = 0; i < numdups; i++) {
                    struct sack_duptsn *dup = (struct sack_duptsn *)(((unsigned char *)sac) + sizeof(struct sack_chunk) + numgaps * sizeof(struct sack_gap) + i * sizeof(struct sack_duptsn));
                    dup->tsn = htonl(sackChunk->getDupTsns(i));
                }
                break;
            }

            case NR_SACK: {
                SctpSackChunk *sackChunk = check_and_cast<SctpSackChunk *>(chunk);

                // destination is send buffer:
                struct nr_sack_chunk *sac = (struct nr_sack_chunk *)(buffer + writtenbytes); // append data to buffer
                writtenbytes += sackChunk->getByteLength();

                // fill buffer with data from Sctp init ack chunk structure
                sac->type = sackChunk->getSctpChunkType();
                sac->flags = 0;
                sac->length = htons(sackChunk->getByteLength());
                uint32_t cumtsnack = sackChunk->getCumTsnAck();
                sac->cum_tsn_ack = htonl(cumtsnack);
                sac->a_rwnd = htonl(sackChunk->getA_rwnd());
                sac->nr_of_gaps = htons(sackChunk->getNumGaps());
                sac->nr_of_dups = htons(sackChunk->getNumDupTsns());

                // GAPs and Dup. TSNs:
                int16_t numgaps = sackChunk->getNumGaps();
                int16_t numdups = sackChunk->getNumDupTsns();
                int16_t numnrgaps = 0;
                for (int16_t i = 0; i < numgaps; i++) {
                    struct sack_gap *gap = (struct sack_gap *)(((unsigned char *)sac) + sizeof(struct nr_sack_chunk) + i * sizeof(struct sack_gap));
                    gap->start = htons(sackChunk->getGapStart(i) - cumtsnack);
                    gap->stop = htons(sackChunk->getGapStop(i) - cumtsnack);
                }
                sac->nr_of_nr_gaps = htons(sackChunk->getNumNrGaps());
                sac->reserved = htons(0);
                numnrgaps = sackChunk->getNumNrGaps();
                for (int16_t i = 0; i < numnrgaps; i++) {
                    struct sack_gap *gap = (struct sack_gap *)(((unsigned char *)sac) + sizeof(struct nr_sack_chunk) + (numgaps + i) * sizeof(struct sack_gap));
                    gap->start = htons(sackChunk->getNrGapStart(i) - cumtsnack);
                    gap->stop = htons(sackChunk->getNrGapStop(i) - cumtsnack);
                }
                for (int16_t i = 0; i < numdups; i++) {
                    struct sack_duptsn *dup = (struct sack_duptsn *)(((unsigned char *)sac) + sizeof(struct nr_sack_chunk) + (numgaps + numnrgaps) * sizeof(struct sack_gap) + i * sizeof(sack_duptsn));
                    dup->tsn = htonl(sackChunk->getDupTsns(i));
                }
                break;
            }

            case HEARTBEAT: {
                EV_INFO << simTime() << "  SctpAssociation:: Heartbeat sent \n";
                SctpHeartbeatChunk *heartbeatChunk = check_and_cast<SctpHeartbeatChunk *>(chunk);

                // destination is send buffer:
                struct heartbeat_chunk *hbc = (struct heartbeat_chunk *)(buffer + writtenbytes); // append data to buffer

                // fill buffer with data from Sctp init ack chunk structure
                hbc->type = heartbeatChunk->getSctpChunkType();

                // deliver info:
                struct heartbeat_info *hbi = (struct heartbeat_info *)(((unsigned char *)hbc) + sizeof(struct heartbeat_chunk));
                L3Address addr = heartbeatChunk->getRemoteAddr();
                simtime_t time = heartbeatChunk->getTimeField();
                int32_t infolen = 0;
#ifdef INET_WITH_IPv4
                if (addr.getType() == L3Address::IPv4) {
                    infolen = sizeof(addr.toIpv4().getInt()) + sizeof(uint32_t);
                    hbi->type = htons(1); // mandatory
                    hbi->length = htons(infolen + 4);
                    struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)hbc) + 8);
                    ipv4addr->type = htons(INIT_PARAM_IPV4);
                    ipv4addr->length = htons(8);
                    ipv4addr->address = htonl(addr.toIpv4().getInt());
                    HBI_ADDR(hbi).v4addr = *ipv4addr;
                }
#endif // ifdef INET_WITH_IPv4
#ifdef INET_WITH_IPv6
                if (addr.getType() == L3Address::IPv6) {
                    infolen = 20 + sizeof(uint32_t);
                    hbi->type = htons(1); // mandatory
                    hbi->length = htons(infolen + 4);
                    struct init_ipv6_address_parameter *ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)hbc) + 8);
                    ipv6addr->type = htons(INIT_PARAM_IPV6);
                    ipv6addr->length = htons(20);
                    for (int32_t j = 0; j < 4; j++) {
                        ipv6addr->address[j] = htonl(addr.toIpv6().words()[j]);
                    }
                    HBI_ADDR(hbi).v6addr = *ipv6addr;
                }
#endif // ifdef INET_WITH_IPv6
                ASSERT(infolen != 0);
                HBI_TIME(hbi) = htonl((uint32_t)time.dbl());
                hbc->length = htons(sizeof(struct heartbeat_chunk) + infolen + 4);
                writtenbytes += sizeof(struct heartbeat_chunk) + infolen + 4;
                break;
            }

            case HEARTBEAT_ACK: {
                EV_INFO << simTime() << " SctpAssociation:: HeartbeatAck sent \n";
                SctpHeartbeatAckChunk *heartbeatAckChunk = check_and_cast<SctpHeartbeatAckChunk *>(chunk);

                // destination is send buffer:
                struct heartbeat_ack_chunk *hbac = (struct heartbeat_ack_chunk *)(buffer + writtenbytes); // append data to buffer

                // fill buffer with data from Sctp init ack chunk structure
                hbac->type = heartbeatAckChunk->getSctpChunkType();

                // deliver info:
                struct heartbeat_info *hbi = (struct heartbeat_info *)(((unsigned char *)hbac) + sizeof(struct heartbeat_ack_chunk));
                int32_t infolen = heartbeatAckChunk->getInfoArraySize();
                hbi->type = htons(1); // mandatory
                if (infolen > 0) {
                    hbi->length = htons(infolen + 4);
                    for (int32_t i = 0; i < infolen; i++) {
                        HBI_INFO(hbi)[i] = heartbeatAckChunk->getInfo(i);
                    }
                }
                else {
                    L3Address addr = heartbeatAckChunk->getRemoteAddr();
                    simtime_t time = heartbeatAckChunk->getTimeField();

#ifdef INET_WITH_IPv4
                    if (addr.getType() == L3Address::IPv4) {
                        infolen = sizeof(addr.toIpv4().getInt()) + sizeof(uint32_t);
                        hbi->type = htons(1); // mandatory
                        hbi->length = htons(infolen + 4);
                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)hbac) + 8);
                        ipv4addr->type = htons(INIT_PARAM_IPV4);
                        ipv4addr->length = htons(8);
                        ipv4addr->address = htonl(addr.toIpv4().getInt());
                        HBI_ADDR(hbi).v4addr = *ipv4addr;
                    }
#endif // ifdef INET_WITH_IPv4
#ifdef INET_WITH_IPv6
                    if (addr.getType() == L3Address::IPv6) {
                        infolen = 20 + sizeof(uint32_t);
                        hbi->type = htons(1); // mandatory
                        hbi->length = htons(infolen + 4);
                        struct init_ipv6_address_parameter *ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)hbac) + 8);
                        ipv6addr->type = htons(INIT_PARAM_IPV6);
                        ipv6addr->length = htons(20);
                        for (int32_t j = 0; j < 4; j++) {
                            ipv6addr->address[j] = htonl(addr.toIpv6().words()[j]);
                        }
                        HBI_ADDR(hbi).v6addr = *ipv6addr;
                    }
#endif // ifdef INET_WITH_IPv6
                    HBI_TIME(hbi) = htonl((uint32_t)time.dbl());
                }
                hbac->length = htons(sizeof(struct heartbeat_ack_chunk) + infolen + 4);
                writtenbytes += sizeof(struct heartbeat_ack_chunk) + infolen + 4;

                break;
            }

            case ABORT: {
                EV_INFO << simTime() << " SctpAssociation:: Abort sent \n";
                SctpAbortChunk *abortChunk = check_and_cast<SctpAbortChunk *>(chunk);

                // destination is send buffer:
                struct abort_chunk *ac = (struct abort_chunk *)(buffer + writtenbytes); // append data to buffer
                writtenbytes += (abortChunk->getByteLength());

                // fill buffer with data from Sctp init ack chunk structure
                ac->type = abortChunk->getSctpChunkType();
                unsigned char flags = 0;
                if (abortChunk->getT_Bit())
                    flags |= T_BIT;
                ac->flags = flags;
                ac->length = htons(abortChunk->getByteLength());
                break;
            }

            case COOKIE_ECHO: {
                EV_INFO << simTime() << " SctpAssociation:: CookieEcho sent \n";
                SctpCookieEchoChunk *cookieChunk = check_and_cast<SctpCookieEchoChunk *>(chunk);

                struct cookie_echo_chunk *cec = (struct cookie_echo_chunk *)(buffer + writtenbytes);

                cec->type = cookieChunk->getSctpChunkType();
                cec->flags = 0; // no flags available in this type of SctpChunk
                cec->length = htons(cookieChunk->getByteLength());
                int32_t cookielen = cookieChunk->getCookieArraySize();
                if (cookielen > 0) {
                    for (int32_t i = 0; i < cookielen; i++)
                        cec->state_cookie[i] = cookieChunk->getCookie(i);
                }
                else {
                    SctpCookie *stateCookie = (SctpCookie *)(cookieChunk->getStateCookie());
                    struct cookie_parameter *cookie = (struct cookie_parameter *)(buffer + writtenbytes + 4);
                    cookie->creationTime = htonl((uint32_t)stateCookie->getCreationTime().dbl());
                    cookie->localTag = htonl(stateCookie->getLocalTag());
                    cookie->peerTag = htonl(stateCookie->getPeerTag());
                    for (int32_t i = 0; i < 32; i++) {
                        cookie->localTieTag[i] = stateCookie->getLocalTieTag(i);
                        cookie->peerTieTag[i] = stateCookie->getPeerTieTag(i);
                    }
                }
                uint32_t paddingEndPos = writtenbytes + ADD_PADDING(cookieChunk->getByteLength());
                writtenbytes += cookieChunk->getByteLength();
                while (writtenbytes < paddingEndPos)
                    buffer[writtenbytes++] = 0;
                uint32_t uLen = cookieChunk->getUnrecognizedParametersArraySize();
                if (uLen > 0) {
                    struct error_chunk *error = (struct error_chunk *)(buffer + writtenbytes);
                    error->type = ERRORTYPE;
                    error->flags = 0;
                    int32_t k = 0;
                    uint32_t pLen = 0;
                    uint32_t ecLen = SCTP_ERROR_CHUNK_LENGTH;
                    uint32_t ecParPtr = 0;
                    while (uLen > 0) {
                        struct tlv *unknown = (struct tlv *)(((unsigned char *)error) + sizeof(struct error_chunk) + ecParPtr);
                        unknown->type = htons(UNRECOGNIZED_PARAMETER);
                        pLen = cookieChunk->getUnrecognizedParameters(k + 2) * 16 + cookieChunk->getUnrecognizedParameters(k + 3);
                        unknown->length = htons(pLen + 4);
                        ecLen += pLen + 4;
                        for (uint32_t i = 0; i < ADD_PADDING(pLen); i++, k++)
                            unknown->value[i] = cookieChunk->getUnrecognizedParameters(k);
                        ecParPtr += ADD_PADDING(pLen + 4);
                        uLen -= ADD_PADDING(pLen);
                    }
                    error->length = htons(ecLen);
                    writtenbytes += SCTP_ERROR_CHUNK_LENGTH + ecParPtr;
                }

                break;
            }

            case COOKIE_ACK: {
                EV_INFO << simTime() << " SctpAssociation:: CookieAck sent \n";
                SctpCookieAckChunk *cookieAckChunk = check_and_cast<SctpCookieAckChunk *>(chunk);

                struct cookie_ack_chunk *cac = (struct cookie_ack_chunk *)(buffer + writtenbytes);
                writtenbytes += cookieAckChunk->getByteLength();

                cac->type = cookieAckChunk->getSctpChunkType();
                cac->length = htons(cookieAckChunk->getByteLength());

                break;
            }

            case SHUTDOWN: {
                EV_INFO << simTime() << " SctpAssociation:: Shutdown sent \n";
                SctpShutdownChunk *shutdownChunk = check_and_cast<SctpShutdownChunk *>(chunk);

                struct shutdown_chunk *sac = (struct shutdown_chunk *)(buffer + writtenbytes);
                writtenbytes += shutdownChunk->getByteLength();

                sac->type = shutdownChunk->getSctpChunkType();
                sac->cumulative_tsn_ack = htonl(shutdownChunk->getCumTsnAck());
                sac->length = htons(shutdownChunk->getByteLength());

                break;
            }

            case SHUTDOWN_ACK: {
                EV_INFO << simTime() << " SctpAssociation:: ShutdownAck sent \n";
                SctpShutdownAckChunk *shutdownAckChunk = check_and_cast<SctpShutdownAckChunk *>(chunk);

                struct shutdown_ack_chunk *sac = (struct shutdown_ack_chunk *)(buffer + writtenbytes);
                writtenbytes += shutdownAckChunk->getByteLength();

                sac->type = shutdownAckChunk->getSctpChunkType();
                sac->length = htons(shutdownAckChunk->getByteLength());

                break;
            }

            case SHUTDOWN_COMPLETE: {
                EV_INFO << simTime() << " SctpAssociation:: ShutdownComplete sent \n";
                SctpShutdownCompleteChunk *shutdownCompleteChunk = check_and_cast<SctpShutdownCompleteChunk *>(chunk);

                struct shutdown_complete_chunk *sac = (struct shutdown_complete_chunk *)(buffer + writtenbytes);
                writtenbytes += shutdownCompleteChunk->getByteLength();

                sac->type = shutdownCompleteChunk->getSctpChunkType();
                sac->length = htons(shutdownCompleteChunk->getByteLength());
                unsigned char flags = 0;
                if (shutdownCompleteChunk->getTBit())
                    flags |= T_BIT;
                sac->flags = flags;
                break;
            }

            case AUTH: {
                SctpAuthenticationChunk *authChunk = check_and_cast<SctpAuthenticationChunk *>(chunk);
                struct auth_chunk *auth = (struct auth_chunk *)(buffer + writtenbytes);
                authstart = writtenbytes;
                writtenbytes += SCTP_AUTH_CHUNK_LENGTH + SHA_LENGTH;
                auth->type = authChunk->getSctpChunkType();
                auth->flags = 0;
                auth->length = htons(SCTP_AUTH_CHUNK_LENGTH + SHA_LENGTH);
                auth->shared_key = htons(authChunk->getSharedKey());
                auth->hmac_identifier = htons(authChunk->getHMacIdentifier());
                for (int i = 0; i < SHA_LENGTH; i++)
                    auth->hmac[i] = 0;
                break;
            }

            case FORWARD_TSN: {
                EV_INFO << simTime() << " SctpAssociation:: ForwardTsn sent" << endl;
                SctpForwardTsnChunk *forward = check_and_cast<SctpForwardTsnChunk *>(chunk);
                struct forward_tsn_chunk *forw = (struct forward_tsn_chunk *)(buffer + writtenbytes);
                writtenbytes += (forward->getByteLength());
                forw->type = forward->getSctpChunkType();
                forw->length = htons(forward->getByteLength());
                forw->cum_tsn = htonl(forward->getNewCumTsn());
                int streamPtr = 0;
                for (unsigned int i = 0; i < forward->getSidArraySize(); i++) {
                    struct forward_tsn_streams *str = (struct forward_tsn_streams *)(((unsigned char *)forw) + sizeof(struct forward_tsn_chunk) + streamPtr);
                    str->sid = htons(forward->getSid(i));
                    str->ssn = htons(forward->getSsn(i));
                    streamPtr += 4;
                }
                break;
            }

            case ASCONF: {
                SctpAsconfChunk *asconfChunk = check_and_cast<SctpAsconfChunk *>(chunk);
                struct asconf_chunk *asconf = (struct asconf_chunk *)(buffer + writtenbytes);
                writtenbytes += (asconfChunk->getByteLength());
                asconf->type = asconfChunk->getSctpChunkType();
                asconf->length = htons(asconfChunk->getByteLength());
                asconf->serial = htonl(asconfChunk->getSerialNumber());
                int parPtr = 0;
                struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                ipv4addr->type = htons(INIT_PARAM_IPV4);
                ipv4addr->length = htons(8);
                ipv4addr->address = htonl(asconfChunk->getAddressParam().toIpv4().getInt());
                parPtr += 8;
                for (unsigned int i = 0; i < asconfChunk->getAsconfParamsArraySize(); i++) {
                    SctpParameter *parameter = (SctpParameter *)(asconfChunk->getAsconfParams(i));
                    switch (parameter->getParameterType()) {
                        case ADD_IP_ADDRESS: {
                            SctpAddIPParameter *addip = check_and_cast<SctpAddIPParameter *>(parameter);
                            struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            parPtr += 8;
                            ip->type = htons(ADD_IP_ADDRESS);
                            ip->correlation_id = htonl(addip->getRequestCorrelationId());
                            struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            ipv4addr->type = htons(INIT_PARAM_IPV4);
                            ipv4addr->length = htons(8);
                            ipv4addr->address = htonl(addip->getAddressParam().toIpv4().getInt());
                            parPtr += 8;
                            ip->length = htons(addip->getByteLength());
                            break;
                        }

                        case DELETE_IP_ADDRESS: {
                            SctpDeleteIPParameter *deleteip = check_and_cast<SctpDeleteIPParameter *>(parameter);
                            struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            parPtr += 8;
                            ip->type = htons(DELETE_IP_ADDRESS);
                            ip->correlation_id = htonl(deleteip->getRequestCorrelationId());
                            struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            ipv4addr->type = htons(INIT_PARAM_IPV4);
                            ipv4addr->length = htons(8);
                            ipv4addr->address = htonl(deleteip->getAddressParam().toIpv4().getInt());
                            parPtr += 8;
                            ip->length = htons(deleteip->getByteLength());
                            break;
                        }

                        case SET_PRIMARY_ADDRESS: {
                            SctpSetPrimaryIPParameter *setip = check_and_cast<SctpSetPrimaryIPParameter *>(parameter);
                            struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            parPtr += 8;
                            ip->type = htons(SET_PRIMARY_ADDRESS);
                            ip->correlation_id = htonl(setip->getRequestCorrelationId());
                            struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf) + sizeof(struct asconf_chunk) + parPtr);
                            ipv4addr->type = htons(INIT_PARAM_IPV4);
                            ipv4addr->length = htons(8);
                            ipv4addr->address = htonl(setip->getAddressParam().toIpv4().getInt());
                            parPtr += 8;
                            ip->length = htons(setip->getByteLength());
                            break;
                        }
                    }
                }
                break;
            }

            case ASCONF_ACK: {
                SctpAsconfAckChunk *asconfAckChunk = check_and_cast<SctpAsconfAckChunk *>(chunk);
                struct asconf_ack_chunk *asconfack = (struct asconf_ack_chunk *)(buffer + writtenbytes);
                writtenbytes += SCTP_ADD_IP_CHUNK_LENGTH;
                asconfack->type = asconfAckChunk->getSctpChunkType();
                asconfack->length = htons(asconfAckChunk->getByteLength());
                asconfack->serial = htonl(asconfAckChunk->getSerialNumber());
                int parPtr = 0;
                for (unsigned int i = 0; i < asconfAckChunk->getAsconfResponseArraySize(); i++) {
                    SctpParameter *parameter = check_and_cast<SctpParameter *>(asconfAckChunk->getAsconfResponse(i));
                    switch (parameter->getParameterType()) {
                        case ERROR_CAUSE_INDICATION: {
                            SctpErrorCauseParameter *error = check_and_cast<SctpErrorCauseParameter *>(parameter);
                            struct add_ip_parameter *addip = (struct add_ip_parameter *)(((unsigned char *)asconfack) + sizeof(struct asconf_ack_chunk) + parPtr);
                            addip->type = htons(error->getParameterType());
                            addip->length = htons(error->getByteLength());
                            addip->correlation_id = htonl(error->getResponseCorrelationId());
                            parPtr += 8;
                            struct error_cause *errorc = (struct error_cause *)(((unsigned char *)asconfack) + sizeof(struct asconf_ack_chunk) + parPtr);
                            errorc->cause_code = htons(error->getErrorCauseType());
                            errorc->length = htons(error->getByteLength() - 8);
                            parPtr += 4;
                            if (check_and_cast<SctpParameter *>(error->getEncapsulatedPacket()) != nullptr) {
                                SctpParameter *encParameter = check_and_cast<SctpParameter *>(error->getEncapsulatedPacket());
                                switch (encParameter->getParameterType()) {
                                    case ADD_IP_ADDRESS: {
                                        SctpAddIPParameter *addip = check_and_cast<SctpAddIPParameter *>(encParameter);
                                        struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause));
                                        parPtr += 8;
                                        ip->type = htons(ADD_IP_ADDRESS);
                                        ip->correlation_id = htonl(addip->getRequestCorrelationId());
                                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause) + 8);
                                        ipv4addr->length = htons(8);
                                        ipv4addr->address = htonl(addip->getAddressParam().toIpv4().getInt());
                                        parPtr += 8;
                                        ip->length = htons(addip->getByteLength());
                                        break;
                                    }

                                    case DELETE_IP_ADDRESS: {
                                        SctpDeleteIPParameter *deleteip = check_and_cast<SctpDeleteIPParameter *>(encParameter);
                                        struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause));
                                        parPtr += 8;
                                        ip->type = htons(DELETE_IP_ADDRESS);
                                        ip->correlation_id = htonl(deleteip->getRequestCorrelationId());
                                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause) + 8);
                                        ipv4addr->type = htons(INIT_PARAM_IPV4);
                                        ipv4addr->length = htons(8);
                                        ipv4addr->address = htonl(deleteip->getAddressParam().toIpv4().getInt());
                                        parPtr += 8;
                                        ip->length = htons(deleteip->getByteLength());
                                        break;
                                    }

                                    case SET_PRIMARY_ADDRESS: {
                                        SctpSetPrimaryIPParameter *setip = check_and_cast<SctpSetPrimaryIPParameter *>(encParameter);
                                        struct add_ip_parameter *ip = (struct add_ip_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause));
                                        parPtr += 8;
                                        ip->type = htons(SET_PRIMARY_ADDRESS);
                                        ip->correlation_id = htonl(setip->getRequestCorrelationId());
                                        struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)errorc) + sizeof(struct error_cause) + 8);
                                        ipv4addr->type = htons(INIT_PARAM_IPV4);
                                        ipv4addr->length = htons(8);
                                        ipv4addr->address = htonl(setip->getAddressParam().toIpv4().getInt());
                                        parPtr += 8;
                                        ip->length = htons(setip->getByteLength());
                                        break;
                                    }
                                }
                            }
                            break;
                        }

                        case SUCCESS_INDICATION: {
                            SctpSuccessIndication *success = check_and_cast<SctpSuccessIndication *>(parameter);
                            struct add_ip_parameter *addip = (struct add_ip_parameter *)(((unsigned char *)asconfack) + sizeof(struct asconf_ack_chunk) + parPtr);
                            addip->type = htons(success->getParameterType());
                            addip->length = htons(8);
                            addip->correlation_id = htonl(success->getResponseCorrelationId());
                            parPtr += 8;
                            break;
                        }
                    }
                }
                writtenbytes += parPtr;
                break;
            }

            case ERRORTYPE: {
                SctpErrorChunk *errorchunk = check_and_cast<SctpErrorChunk *>(chunk);
                struct error_chunk *error = (struct error_chunk *)(buffer + writtenbytes);
                error->type = errorchunk->getSctpChunkType();
                uint16_t flags = 0;
                if (errorchunk->getMBit())
                    flags |= NAT_M_FLAG;
                if (errorchunk->getTBit())
                    flags |= NAT_T_FLAG;
                error->flags = flags;
                error->length = htons(errorchunk->getByteLength());

                if (errorchunk->getParametersArraySize() > 0) {
                    SctpParameter *parameter = check_and_cast<SctpParameter *>(errorchunk->getParameters(0));
                    switch (parameter->getParameterType()) {
                        case MISSING_NAT_ENTRY: {
                            SctpSimpleErrorCauseParameter *ecp = check_and_cast<SctpSimpleErrorCauseParameter *>(parameter);
                            struct error_cause *errorc = (struct error_cause *)(((unsigned char *)error) + sizeof(struct error_chunk));
                            errorc->cause_code = htons(ecp->getParameterType());
                            /* ToDo */
                          /*  if (check_and_cast<Ipv4Header *>(ecp->getEncapsulatedPacket()) != nullptr) {
                                Buffer b((unsigned char *)error + sizeof(struct error_chunk) + 4, ecp->getByteLength() - 4);
                                Context c;
                                Ipv4Serializer().serializePacket(ecp->getEncapsulatedPacket(), b, c);
                            }*/
                            errorc->length = htons(ecp->getByteLength());
                            break;
                        }
                        case INVALID_STREAM_IDENTIFIER: {
                            SctpSimpleErrorCauseParameter *ecp = check_and_cast<SctpSimpleErrorCauseParameter *>(parameter);
                            struct error_cause_with_int *errorc = (struct error_cause_with_int *)(((unsigned char *)error) + sizeof(struct error_chunk));
                            errorc->cause_code = htons(ecp->getParameterType());
                            errorc->length = htons(ecp->getByteLength());
                            errorc->info = htons(ecp->getValue());
                            errorc->reserved = 0;
                            break;
                        }
                        default: EV_WARN << "Error cause " << parameter->getParameterType() << " not implemented\n";
                    }
                    writtenbytes += errorchunk->getByteLength();
                }
                else
                    writtenbytes += ADD_PADDING(error->length);
                break;
            }

            case RE_CONFIG: {
                SctpStreamResetChunk *streamReset = check_and_cast<SctpStreamResetChunk *>(chunk);
                struct stream_reset_chunk *stream = (struct stream_reset_chunk *)(buffer + writtenbytes);
                writtenbytes += (streamReset->getByteLength());
                stream->type = streamReset->getSctpChunkType();
                int parPtr = 0;
                uint16_t numParameters = streamReset->getParametersArraySize();
                for (int i = 0; i < numParameters; i++) {
                    SctpParameter *parameter = (SctpParameter *)(streamReset->getParameters(i));
                    switch (parameter->getParameterType()) {
                        case OUTGOING_RESET_REQUEST_PARAMETER: {
                            SctpOutgoingSsnResetRequestParameter *outparam = check_and_cast<SctpOutgoingSsnResetRequestParameter *>(parameter);
                            struct outgoing_reset_request_parameter *out = (outgoing_reset_request_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            out->type = htons(outparam->getParameterType());
                            out->srReqSn = htonl(outparam->getSrReqSn());
                            out->srResSn = htonl(outparam->getSrResSn());
                            out->lastTsn = htonl(outparam->getLastTsn());
                            parPtr += sizeof(struct outgoing_reset_request_parameter);
                            if (outparam->getStreamNumbersArraySize() > 0) {
                                for (unsigned int j = 0; j < outparam->getStreamNumbersArraySize(); j++) {
                                    out->streamNumbers[j] = htons(outparam->getStreamNumbers(j));
                                }
                                if (i < numParameters - 1) {
                                    parPtr += ADD_PADDING(outparam->getStreamNumbersArraySize() * 2);
                                }
                                else {
                                    parPtr += outparam->getStreamNumbersArraySize() * 2;
                                }
                            }
                            out->length = htons(sizeof(struct outgoing_reset_request_parameter) + outparam->getStreamNumbersArraySize() * 2);
                            break;
                        }

                        case INCOMING_RESET_REQUEST_PARAMETER: {
                            SctpIncomingSsnResetRequestParameter *inparam = check_and_cast<SctpIncomingSsnResetRequestParameter *>(parameter);
                            struct incoming_reset_request_parameter *in = (incoming_reset_request_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            in->type = htons(inparam->getParameterType());
                            in->srReqSn = htonl(inparam->getSrReqSn());
                            parPtr += sizeof(struct incoming_reset_request_parameter);
                            if (inparam->getStreamNumbersArraySize() > 0) {
                                for (unsigned int j = 0; j < inparam->getStreamNumbersArraySize(); j++) {
                                    in->streamNumbers[j] = htons(inparam->getStreamNumbers(j));
                                }
                                if (i < numParameters - 1) {
                                    parPtr += ADD_PADDING(inparam->getStreamNumbersArraySize() * 2);
                                }
                                else {
                                    parPtr += inparam->getStreamNumbersArraySize() * 2;
                                }
                            }
                            in->length = htons(sizeof(struct incoming_reset_request_parameter) + inparam->getStreamNumbersArraySize() * 2);
                            break;
                        }

                        case SSN_TSN_RESET_REQUEST_PARAMETER: {
                            SctpSsnTsnResetRequestParameter *ssnparam = check_and_cast<SctpSsnTsnResetRequestParameter *>(parameter);
                            struct ssn_tsn_reset_request_parameter *ssn = (struct ssn_tsn_reset_request_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            ssn->type = htons(ssnparam->getParameterType());
                            ssn->length = htons(8);
                            ssn->srReqSn = htonl(ssnparam->getSrReqSn());
                            parPtr += sizeof(struct ssn_tsn_reset_request_parameter);
                            break;
                        }

                        case STREAM_RESET_RESPONSE_PARAMETER: {
                            SctpStreamResetResponseParameter *response = check_and_cast<SctpStreamResetResponseParameter *>(parameter);
                            struct stream_reset_response_parameter *resp = (struct stream_reset_response_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            resp->type = htons(response->getParameterType());
                            resp->srResSn = htonl(response->getSrResSn());
                            resp->result = htonl(response->getResult());
                            resp->length = htons(12);
                            parPtr += 12;
                            if (response->getSendersNextTsn() != 0) {
                                resp->sendersNextTsn = htonl(response->getSendersNextTsn());
                                resp->receiversNextTsn = htonl(response->getReceiversNextTsn());
                                resp->length = htons(20);
                                parPtr += 8;
                            }
                            break;
                        }

                        case ADD_INCOMING_STREAMS_REQUEST_PARAMETER: {
                            SctpAddStreamsRequestParameter *instreams = check_and_cast<SctpAddStreamsRequestParameter *>(parameter);
                            struct add_streams_request_parameter *addinp = (struct add_streams_request_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            addinp->type = htons(instreams->getParameterType());
                            addinp->srReqSn = htonl(instreams->getSrReqSn());
                            addinp->numberOfStreams = htons(instreams->getNumberOfStreams());
                            addinp->reserved = 0;
                            addinp->length = htons(12);
                            parPtr += 12;
                            break;
                        }

                        case ADD_OUTGOING_STREAMS_REQUEST_PARAMETER: {
                            SctpAddStreamsRequestParameter *outstreams = check_and_cast<SctpAddStreamsRequestParameter *>(parameter);
                            struct add_streams_request_parameter *addoutp = (struct add_streams_request_parameter *)(((unsigned char *)stream) + sizeof(struct stream_reset_chunk) + parPtr);
                            addoutp->type = htons(outstreams->getParameterType());
                            addoutp->srReqSn = htonl(outstreams->getSrReqSn());
                            addoutp->numberOfStreams = htons(outstreams->getNumberOfStreams());
                            addoutp->reserved = 0;
                            addoutp->length = htons(12);
                            parPtr += 12;
                            break;
                        }
                    }
                }
                stream->length = htons(SCTP_STREAM_RESET_CHUNK_LENGTH + parPtr);
                break;
            }

            case PKTDROP: {
                SctpPacketDropChunk *packetdrop = check_and_cast<SctpPacketDropChunk *>(chunk);
                struct pktdrop_chunk *drop = (struct pktdrop_chunk *)(buffer + writtenbytes);
                unsigned char flags = 0;
                if (packetdrop->getCFlag())
                    flags |= C_FLAG;
                if (packetdrop->getTFlag())
                    flags |= T_FLAG;
                if (packetdrop->getBFlag())
                    flags |= B_FLAG;
                if (packetdrop->getMFlag())
                    flags |= M_FLAG;
                drop->flags = flags;
                drop->type = packetdrop->getSctpChunkType();
                drop->max_rwnd = htonl(packetdrop->getMaxRwnd());
                drop->queued_data = htonl(packetdrop->getQueuedData());
                drop->trunc_length = htons(packetdrop->getTruncLength());
                drop->reserved = 0;
                SctpHeader *msg = check_and_cast<SctpHeader *>(packetdrop->getEncapsulatedPacket());
                int msglen = msg->getChunkLength().get<B>();
                drop->length = htons(SCTP_PKTDROP_CHUNK_LENGTH + msglen);
//                int len = serialize(msg, drop->dropped_data, msglen);
                writtenbytes += (packetdrop->getByteLength());
                break;
            }

            default:
                throw cRuntimeError("TODO unknown chunktype in outgoing packet on external interface! Implement it!");
        }
    }
    // calculate the HMAC if required
    uint8_t result[SHA_LENGTH];
    if (authstart != 0) {
        struct data_vector *ac = (struct data_vector *)(buffer + authstart);
        EV_DETAIL << "sizeKeyVector=" << keys.sizeKeyVector << ", sizePeerKeyVector=" << keys.sizePeerKeyVector << "\n";
        hmacSha1((uint8_t *)ac->data, writtenbytes - authstart, keys.sharedKey, keys.sizeKeyVector + keys.sizePeerKeyVector, result);
        struct auth_chunk *auth = (struct auth_chunk *)(buffer + authstart);
        for (int32_t k = 0; k < SHA_LENGTH; k++)
            auth->hmac[k] = result[k];
    }
    // finally, set the CHECKSUM32 checksum field in the Sctp common header
    ch->checksum = crc32c((unsigned char *)buffer, writtenbytes);
    // check the serialized packet length
    if (writtenbytes != msg->getChunkLength().get<B>()) {
        throw cRuntimeError("Sctp Serializer error: writtenbytes (%lu) != msgLength(%lu) in message (%s)%s",
                (unsigned long)writtenbytes, (unsigned long)msg->getChunkLength().get<B>(), msg->getClassName(), msg->getFullName());
    }
    stream.writeBytes((uint8_t *)&buffer, B(writtenbytes));
}

void SctpHeaderSerializer::hmacSha1(const uint8_t *buf, uint32_t buflen, const uint8_t *key, uint32_t keylen, uint8_t *digest)
{
    /* TODO needs to be implemented */
    for (uint16_t i = 0; i < SHA_LENGTH; i++) {
        digest[i] = 0;
    }
}

const Ptr<Chunk> SctpHeaderSerializer::deserialize(MemoryInputStream& stream) const
{
    uint16_t paramType;
    int32_t parptr, chunklen, cLen, woPadding;

//    auto position = stream.getPosition();
    int bufsize = stream.getRemainingLength().get<B>();
    uint8_t *buffer = new uint8_t[bufsize];
    stream.readBytes(buffer, B(bufsize));
    auto dest = makeShared<SctpHeader>();

    struct common_header *common_header = (struct common_header *)((void *)buffer);
    int32_t tempChecksum = common_header->checksum;
    common_header->checksum = 0;
    int32_t chksum = crc32c((unsigned char *)common_header, bufsize);
    common_header->checksum = tempChecksum;

    const unsigned char *chunks = (unsigned char *)(buffer + sizeof(struct common_header));
    EV_TRACE << "SctpSerializer::parse SctpHeader\n";
    if (tempChecksum == chksum)
        dest->setChecksumOk(true);
    else
        dest->setChecksumOk(false);
    EV_DETAIL << "checksumOK=" << dest->getChecksumOk() << "\n";
    dest->setSrcPort(ntohs(common_header->source_port));
    dest->setDestPort(ntohs(common_header->destination_port));
    dest->setVTag(ntohl(common_header->verification_tag));
    dest->setChunkLength(B(SCTP_COMMON_HEADER));
    dest->setChecksumMode(CHECKSUM_COMPUTED);
    dest->setChecksum(common_header->checksum);
    // chunks
    uint32_t chunkPtr = 0;

    // catch ALL chunks - when a chunk is taken, the chunkPtr is set to the next chunk
    while (chunkPtr < (bufsize - sizeof(struct common_header))) {
        const struct chunk *chunk = (struct chunk *)(chunks + chunkPtr);
        int32_t chunkType = chunk->type;
        woPadding = ntohs(chunk->length);
        if (woPadding == 0) {
            delete [] buffer;
            return dest;
        }
        cLen = ADD_PADDING(woPadding);
        switch (chunkType) {
            case DATA: {
                EV_INFO << "Data received\n";
                const struct data_chunk *dc = (struct data_chunk *)(chunks + chunkPtr);
                EV_DETAIL << "cLen=" << cLen << "\n";
                if (cLen == 0)
                    throw cRuntimeError("Incoming SCTP packet contains data chunk with length==0");
                SctpDataChunk *chunk = new SctpDataChunk("DATA");
                chunk->setSctpChunkType(chunkType);
                chunk->setUBit(dc->flags & UNORDERED_BIT);
                chunk->setBBit(dc->flags & BEGIN_BIT);
                chunk->setEBit(dc->flags & END_BIT);
                chunk->setIBit(dc->flags & I_BIT);
                chunk->setTsn(ntohl(dc->tsn));
                chunk->setSid(ntohs(dc->sid));
                chunk->setSsn(ntohs(dc->ssn));
                chunk->setPpid(ntohl(dc->ppi));
                chunk->setByteLength(SCTP_DATA_CHUNK_LENGTH);
                EV_DETAIL << "parse data: woPadding=" << woPadding << " size_data_chunk=" << sizeof(struct data_chunk) << "\n";
                if (woPadding > (int)sizeof(struct data_chunk)) {
                    SctpSimpleMessage *msg = new SctpSimpleMessage("data");
                    int32_t datalen = (woPadding - sizeof(struct data_chunk));
                    msg->setBitLength(datalen * 8);
                    msg->setDataLen(datalen);
                    msg->setDataArraySize(datalen);
                    for (int32_t i = 0; i < datalen; i++)
                        msg->setData(i, dc->user_data[i]);

                    chunk->encapsulate(msg);
                }
                EV_DETAIL << "datachunkLength=" << chunk->getByteLength() << "\n";
                dest->appendSctpChunks(chunk);
                break;
            }

            case INIT: {
                EV << "parse INIT\n";
                const struct init_chunk *init_chunk = (struct init_chunk *)(chunks + chunkPtr); // (recvBuffer + size_ip + sizeof(struct common_header));
                struct tlv *cp;
                struct random_parameter *rp;
                struct hmac_algo *hp;
                unsigned int rplen = 0, hplen = 0, cplen = 0;
                chunklen = SCTP_INIT_CHUNK_LENGTH;
                SctpInitChunk *chunk = new SctpInitChunk("INIT");
                chunk->setSctpChunkType(chunkType);
                chunk->setName("INIT");
                chunk->setInitTag(ntohl(init_chunk->initiate_tag));
                chunk->setA_rwnd(ntohl(init_chunk->a_rwnd));
                chunk->setNoOutStreams(ntohs(init_chunk->mos));
                chunk->setNoInStreams(ntohs(init_chunk->mis));
                chunk->setInitTsn(ntohl(init_chunk->initial_tsn));
                chunk->setAddressesArraySize(0);
                chunk->setUnrecognizedParametersArraySize(0);
//                sctpEV3<<"INIT arrived from wire\n";
                if (cLen > (int)sizeof(struct init_chunk)) {
                    int32_t addrcounter = 0;
                    parptr = 0;
                    int chkcounter = 0;
                    bool stopProcessing = false;
                    while (cLen > (int)sizeof(struct init_chunk) + parptr && !stopProcessing) {
                        EV_INFO << "Process INIT parameters" << endl;
                        const struct tlv *parameter = (struct tlv *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                        paramType = ntohs(parameter->type);
                        EV_INFO << "search for param: " << paramType << " - current chunklen: " << chunklen << endl;
                        switch (paramType) {
                            case SUPPORTED_ADDRESS_TYPES: {
                                const struct supported_address_types_parameter *sup_addr = (struct supported_address_types_parameter *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                if (sup_addr->address_type_1 == ntohs(INIT_PARAM_IPV4) || sup_addr->address_type_2 == ntohs(INIT_PARAM_IPV4)) {
                                    chunk->setIpv4Supported(true);
                                }
                                else {
                                    chunk->setIpv4Supported(false);
                                }
                                if (sup_addr->address_type_1 == ntohs(INIT_PARAM_IPV6) || sup_addr->address_type_2 == ntohs(INIT_PARAM_IPV6)) {
                                    chunk->setIpv6Supported(true);
                                }
                                else {
                                    chunk->setIpv6Supported(false);
                                }
                                chunklen += 8;
                                break;
                            }

                            case INIT_PARAM_IPV4: {
                                // we supppose an ipv4 address parameter
                                EV_INFO << "IPv4\n";
                                const struct init_ipv4_address_parameter *v4addr;
                                v4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                chunk->setAddressesArraySize(++addrcounter);
                                L3Address localv4Addr(Ipv4Address(ntohl(v4addr->address)));
                                chunk->setAddresses(addrcounter - 1, localv4Addr);
                                chunklen += 8;
                                break;
                            }

                            case INIT_PARAM_IPV6: {
                                EV_INFO << "IPv6\n";
                                const struct init_ipv6_address_parameter *ipv6addr;
                                ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                Ipv6Address ipv6Addr = Ipv6Address(ipv6addr->address[0], ipv6addr->address[1],
                                        ipv6addr->address[2], ipv6addr->address[3]);
                                L3Address localv6Addr(ipv6Addr);
                                EV_INFO << "address" << ipv6Addr << "\n";
                                chunk->setAddressesArraySize(++addrcounter);
                                chunk->setAddresses(addrcounter - 1, localv6Addr);
                                chunklen += 20;
                                break;
                            }

                            case SUPPORTED_EXTENSIONS: {
                                EV_INFO << "Supported extensions\n";
                                const struct supported_extensions_parameter *supext;
                                supext = (struct supported_extensions_parameter *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                unsigned short chunkTypes;
                                int len = 4;
                                EV_INFO << "supext->len=" << ntohs(supext->length) << "\n";
                                while (ntohs(supext->length) > len) {
                                    chunkTypes = (int)*(chunks + chunkPtr + sizeof(struct init_chunk) + parptr + 4 + chkcounter);
                                    chunk->setSepChunksArraySize(++chkcounter);
                                    EV_INFO << "Extension " << chunkTypes << " added\n";
                                    chunk->setSepChunks(chkcounter - 1, chunkTypes);
                                    len++;
                                }
                                chunklen += ADD_PADDING(len);
                                break;
                            }

                            case FORWARD_TSN_SUPPORTED_PARAMETER: {
                                EV_INFO << "Forward TSN\n";
                                int size = chunk->getSctpChunkTypesArraySize();
                                chunk->setSctpChunkTypesArraySize(size + 1);
                                chunk->setSctpChunkTypes(size, FORWARD_TSN_SUPPORTED_PARAMETER);
                                chunklen += ntohs(parameter->length);
                                break;
                            }

                            case RANDOM: {
                                EV_INFO << "random parameter received\n";
                                const struct random_parameter *rand;
                                rand = (struct random_parameter *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                unsigned char *rv = (unsigned char *)malloc(64);
                                rp = (struct random_parameter *)(rv);
                                rp->type = rand->type;
                                rplen = ntohs(rand->length);
                                rp->length = rand->length;
                                int rlen = ntohs(rand->length) - 4;
                                chunk->setRandomArraySize(rlen);
                                for (int i = 0; i < rlen; i++) {
                                    chunk->setRandom(i, rand->random[i]);
                                    rp->random[i] = rand->random[i];
                                }
                                EV_INFO << "adding " << ntohs(parameter->length) << " bytes" << endl;
                                chunklen += ntohs(parameter->length);
                                break;
                            }

                            case HMAC_ALGO: {
                                EV_INFO << "hmac_algo parameter received\n";
                                const struct hmac_algo *hmac;
                                hmac = (struct hmac_algo *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                int num = (ntohs(hmac->length) - 4) / 2;
                                chunk->setHmacTypesArraySize(num);
                                unsigned char *hv = (unsigned char *)malloc(64);
                                hp = (struct hmac_algo *)(hv);
                                hp->type = hmac->type;
                                hplen = ntohs(hmac->length);
                                hp->length = hmac->length;
                                for (int i = 0; i < num; i++) {
                                    chunk->setHmacTypes(i, ntohs(hmac->ident[i]));
                                    hp->ident[i] = hmac->ident[i];
                                }
                                chunklen += 4 + 2 * num;
                                break;
                            }

                            case CHUNKS: {
                                EV_INFO << "chunks parameter received\n";
                                const struct tlv *chunks;
                                chunks = (struct tlv *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);
                                unsigned char *cv = (unsigned char *)malloc(64);
                                cp = (struct tlv *)(cv);
                                cp->type = chunks->type;
                                cplen = ntohs(chunks->length);
                                cp->length = chunks->length;
                                int num = cplen - 4;
                                chunk->setSctpChunkTypesArraySize(num);
                                for (int i = 0; i < num; i++) {
                                    chunk->setSctpChunkTypes(i, (chunks->value[i]));
                                    cp->value[i] = chunks->value[i];
                                }
                                chunklen += ADD_PADDING(ntohs(parameter->length));
                                break;
                            }

                            default: {
                                EV_INFO << "Unknown Sctp INIT parameter type " << paramType << "\n";
                                uint16_t skip = (paramType & 0x8000) >> 15;
                                if (skip == 0)
                                    stopProcessing = true;
                                uint16_t report = (paramType & 0x4000) >> 14;

                                const struct tlv *unknown;
                                unknown = (struct tlv *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);

                                if (report != 0) {
                                    uint32_t unknownLen = chunk->getUnrecognizedParametersArraySize();
                                    chunk->setUnrecognizedParametersArraySize(unknownLen + ADD_PADDING(ntohs(unknown->length)));
                                    struct data_vector *dv = (struct data_vector *)(((unsigned char *)init_chunk) + sizeof(struct init_chunk) + parptr);

                                    for (uint32_t i = unknownLen; i < unknownLen + ADD_PADDING(ntohs(unknown->length)); i++)
                                        chunk->setUnrecognizedParameters(i, dv->data[i - unknownLen]);
                                }
                                else {
                                    chunklen += ADD_PADDING(ntohs(unknown->length));
                                }
                                EV_INFO << "stopProcessing=" << stopProcessing << " report=" << report << "\n";
                                break;
                            }
                        }
                        parptr += ADD_PADDING(ntohs(parameter->length));
                    }
                }
                if (chunk->getHmacTypesArraySize() != 0) {
                    unsigned char *vector = (unsigned char *)malloc(64);
                    keys.sizePeerKeyVector = rplen;
                    memcpy(vector, rp, rplen);
                    for (unsigned int k = 0; k < keys.sizePeerKeyVector; k++) {
                        keys.peerKeyVector[k] = vector[k];
                    }
                    memcpy(vector, cp, cplen);
                    for (unsigned int k = 0; k < cplen; k++) {
                        keys.peerKeyVector[keys.sizePeerKeyVector + k] = vector[k];
                    }
                    keys.sizePeerKeyVector += cplen;
                    memcpy(vector, hp, hplen);
                    for (unsigned int k = 0; k < hplen; k++) {
                        keys.peerKeyVector[keys.sizePeerKeyVector + k] = vector[k];
                    }
                    keys.sizePeerKeyVector += hplen;
                    free(vector);
                }
                chunk->setBitLength(chunklen * 8);
                EV_INFO << "chunklen: " << chunk->getByteLength() << endl;
                dest->appendSctpChunks(chunk);
//                chunkPtr += cLen;
                break;
            }

            case INIT_ACK: {
                const struct init_ack_chunk *iac = (struct init_ack_chunk *)(chunks + chunkPtr);
                struct tlv *cp = nullptr;
                struct random_parameter *rp = nullptr;
                struct hmac_algo *hp = nullptr;
                unsigned int rplen = 0, hplen = 0, cplen = 0;
                chunklen = SCTP_INIT_CHUNK_LENGTH;
                SctpInitAckChunk *chunk = new SctpInitAckChunk("INIT_ACK");
                chunk->setSctpChunkType(chunkType);
                chunk->setInitTag(ntohl(iac->initiate_tag));
                chunk->setA_rwnd(ntohl(iac->a_rwnd));
                chunk->setNoOutStreams(ntohs(iac->mos));
                chunk->setNoInStreams(ntohs(iac->mis));
                chunk->setInitTsn(ntohl(iac->initial_tsn));
                chunk->setUnrecognizedParametersArraySize(0);
                if (cLen > (int)sizeof(struct init_ack_chunk)) {
                    int32_t addrcounter = 0;
                    parptr = 0;
                    int chkcounter = 0;
                    bool stopProcessing = false;
//                    sctpEV3<<"cLen="<<cLen<<"\n";
                    while (cLen > (int)sizeof(struct init_ack_chunk) + parptr && !stopProcessing) {
                        const struct tlv *parameter = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                        paramType = ntohs(parameter->type);

                        EV_INFO << "Chunklen before: " << chunklen << endl;
                        switch (paramType) {
                            case SUPPORTED_ADDRESS_TYPES: {
                                const struct supported_address_types_parameter *sup_addr = (struct supported_address_types_parameter *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                if (sup_addr->address_type_1 == ntohs(INIT_PARAM_IPV4) || sup_addr->address_type_2 == ntohs(INIT_PARAM_IPV4)) {
                                    chunk->setIpv4Supported(true);
                                }
                                else {
                                    chunk->setIpv4Supported(false);
                                }
                                if (sup_addr->address_type_1 == ntohs(INIT_PARAM_IPV6) || sup_addr->address_type_2 == ntohs(INIT_PARAM_IPV6)) {
                                    chunk->setIpv6Supported(true);
                                }
                                else {
                                    chunk->setIpv6Supported(false);
                                }
                                chunklen += 8;
                                break;
                            }

                            case INIT_PARAM_IPV4: {
                                EV_INFO << "parse IPv4\n";
                                const struct init_ipv4_address_parameter *v4addr;
                                v4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                chunk->setAddressesArraySize(++addrcounter);
                                L3Address localv4Addr(Ipv4Address(ntohl(v4addr->address)));
                                chunk->setAddresses(addrcounter - 1, localv4Addr);
                                chunklen += 8;
                                break;
                            }

                            case INIT_PARAM_IPV6: {
                                EV_INFO << "IPv6\n";
                                const struct init_ipv6_address_parameter *ipv6addr;
                                ipv6addr = (struct init_ipv6_address_parameter *)(((unsigned char *)iac) + sizeof(struct init_chunk) + parptr);
                                Ipv6Address ipv6Addr = Ipv6Address(ipv6addr->address[0], ipv6addr->address[1],
                                        ipv6addr->address[2], ipv6addr->address[3]);
                                EV_INFO << "address" << ipv6Addr << "\n";
                                L3Address localv6Addr(ipv6Addr);

                                chunk->setAddressesArraySize(++addrcounter);
                                chunk->setAddresses(addrcounter - 1, localv6Addr);
                                chunklen += 20;
                                break;
                            }

                            case RANDOM: {
                                const struct random_parameter *rand;
                                rand = (struct random_parameter *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                int rlen = ntohs(rand->length) - 4;
                                chunk->setRandomArraySize(rlen);
                                rp = (struct random_parameter *)((unsigned char *)malloc(64));
                                rp->type = rand->type;
                                rplen = ntohs(rand->length);
                                rp->length = rand->length;
                                for (int i = 0; i < rlen; i++) {
                                    chunk->setRandom(i, (unsigned char)(rand->random[i]));
                                    rp->random[i] = (unsigned char)(rand->random[i]);
                                }

                                chunklen += ntohs(parameter->length);
                                break;
                            }

                            case HMAC_ALGO: {
                                const struct hmac_algo *hmac;
                                hmac = (struct hmac_algo *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                int num = (ntohs(hmac->length) - 4) / 2;
                                chunk->setHmacTypesArraySize(num);
                                hp = (struct hmac_algo *)((unsigned char *)malloc(64));
                                hp->type = hmac->type;
                                hplen = ntohs(hmac->length);
                                hp->length = hmac->length;
                                for (int i = 0; i < num; i++) {
                                    chunk->setHmacTypes(i, ntohs(hmac->ident[i]));
                                    hp->ident[i] = hmac->ident[i];
                                }
                                chunklen += 4 + 2 * num;
                                break;
                            }

                            case CHUNKS: {
                                const struct tlv *chunks;
                                chunks = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                int num = ntohs(chunks->length) - 4;
                                chunk->setSctpChunkTypesArraySize(num);
                                cp = (struct tlv *)((unsigned char *)malloc(64));
                                cp->type = chunks->type;
                                cplen = ntohs(chunks->length);
                                cp->length = chunks->length;
                                for (int i = 0; i < num; i++) {
                                    chunk->setSctpChunkTypes(i, chunks->value[i]);
                                    cp->value[i] = chunks->value[i];
                                }
                                chunklen += ADD_PADDING(ntohs(parameter->length));
                                break;
                            }

                            case INIT_PARAM_COOKIE: {
                                const struct tlv *cookie = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                int32_t cookieLen = ntohs(cookie->length) - 4;
                                // put cookie data into chunk (char array cookie)
                                chunk->setCookieArraySize(cookieLen);
                                for (int32_t i = 0; i < cookieLen; i++)
                                    chunk->setCookie(i, cookie->value[i]);
                                chunklen += cookieLen + 4;
                                break;
                            }

                            case SUPPORTED_EXTENSIONS: {
                                const struct supported_extensions_parameter *supext;
                                supext = (struct supported_extensions_parameter *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);
                                unsigned short chunkTypes;
//                                chunklen += 4;
                                int len = 4;
                                while (ntohs(supext->length) > len) {
                                    chunkTypes = (int)*(chunks + chunkPtr + sizeof(struct init_ack_chunk) + parptr + 4 + chkcounter);
                                    chunk->setSepChunksArraySize(++chkcounter);
                                    chunk->setSepChunks(chkcounter - 1, chunkTypes);
//                                    chunklen++;
                                    len++;
                                }
                                chunklen += ADD_PADDING(len);
                                break;
                            }

                            case FORWARD_TSN_SUPPORTED_PARAMETER: {
                                int size = chunk->getSctpChunkTypesArraySize();
                                chunk->setSctpChunkTypesArraySize(size + 1);
                                chunk->setSctpChunkTypes(size, FORWARD_TSN_SUPPORTED_PARAMETER);
                                chunklen++;
                                break;
                            }

                            default: {
                                EV_INFO << "Unknown SCTP INIT-ACK parameter type " << paramType << "\n";
                                uint16_t skip = (paramType & 0x8000) >> 15;
                                if (skip == 0)
                                    stopProcessing = true;
                                uint16_t report = (paramType & 0x4000) >> 14;

                                const struct tlv *unknown;
                                unknown = (struct tlv *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);

                                if (report != 0) {
                                    uint32_t unknownLen = chunk->getUnrecognizedParametersArraySize();
                                    chunk->setUnrecognizedParametersArraySize(unknownLen + ADD_PADDING(ntohs(unknown->length)));
                                    struct data_vector *dv = (struct data_vector *)(((unsigned char *)iac) + sizeof(struct init_ack_chunk) + parptr);

                                    for (uint32_t i = unknownLen; i < unknownLen + ADD_PADDING(ntohs(unknown->length)); i++)
                                        chunk->setUnrecognizedParameters(i, dv->data[i - unknownLen]);
                                }
                                else {
                                    chunklen += ADD_PADDING(ntohs(unknown->length));
                                }
                                EV_INFO << "stopProcessing=" << stopProcessing << "  report=" << report << "\n";

                                break;
                            }
                        }
                        EV_INFO << "Chunklen after: " << chunklen << endl;
                        parptr += ADD_PADDING(ntohs(parameter->length));
                    }
                }
                if (chunk->getHmacTypesArraySize() != 0) {
                    unsigned char vector[64];
                    if (rplen > 64) {
                        EV_ERROR << "Random parameter too long. It will be truncated.\n";
                        rplen = 64;
                    }
                    keys.sizePeerKeyVector = rplen;
                    memcpy(vector, rp, rplen);
                    for (unsigned int k = 0; k < keys.sizePeerKeyVector; k++) {
                        keys.peerKeyVector[k] = vector[k];
                    }
                    free(rp);
                    if (cplen > 64) {
                        EV_ERROR << "Chunks parameter too long. It will be truncated.\n";
                        cplen = 64;
                    }
                    memcpy(vector, cp, cplen);
                    for (unsigned int k = 0; k < cplen; k++) {
                        keys.peerKeyVector[keys.sizePeerKeyVector + k] = vector[k];
                    }
                    free(cp);
                    keys.sizePeerKeyVector += cplen;
                    if (hplen > 64) {
                        EV_ERROR << "HMac parameter too long. It will be truncated.\n";
                        hplen = 64;
                    }
                    memcpy(vector, hp, hplen);
                    for (unsigned int k = 0; k < hplen; k++) {
                        keys.peerKeyVector[keys.sizePeerKeyVector + k] = vector[k];
                    }
                    free(hp);
                    keys.sizePeerKeyVector += hplen;
//                    calculateSharedKey();
                }
                chunk->setByteLength(chunklen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case SACK: {
                EV << "SctpHeader: SACK received\n";
                const struct sack_chunk *sac = (struct sack_chunk *)(chunks + chunkPtr);
                SctpSackChunk *chunk = new SctpSackChunk("SACK");
                chunk->setSctpChunkType(chunkType);
                uint32_t cumtsnack = ntohl(sac->cum_tsn_ack);
                chunk->setCumTsnAck(cumtsnack);
                chunk->setA_rwnd(ntohl(sac->a_rwnd));

                int32_t ngaps = ntohs(sac->nr_of_gaps);
                int32_t ndups = ntohs(sac->nr_of_dups);
                chunk->setNumGaps(ngaps);
                chunk->setNumDupTsns(ndups);

                chunk->setGapStartArraySize(ngaps);
                chunk->setGapStopArraySize(ngaps);
                chunk->setDupTsnsArraySize(ndups);

                for (int32_t i = 0; i < ngaps; i++) {
                    const struct sack_gap *gap = (struct sack_gap *)(((unsigned char *)sac) + sizeof(struct sack_chunk) + i * sizeof(sack_gap));
                    chunk->setGapStart(i, ntohs(gap->start) + cumtsnack);
                    chunk->setGapStop(i, ntohs(gap->stop) + cumtsnack);
                }
                for (int32_t i = 0; i < ndups; i++) {
                    const struct sack_duptsn *dup = (struct sack_duptsn *)(((unsigned char *)sac) + sizeof(struct sack_chunk) + ngaps * sizeof(sack_gap) + i * sizeof(sack_duptsn));
                    chunk->setDupTsns(i, ntohl(dup->tsn));
                }

                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case HEARTBEAT: {
                const struct heartbeat_chunk *hbc = (struct heartbeat_chunk *)(chunks + chunkPtr);
                SctpHeartbeatChunk *chunk = new SctpHeartbeatChunk("HEARTBEAT");
                chunk->setSctpChunkType(chunkType);
                if (cLen > (int)sizeof(struct heartbeat_chunk)) {
                    parptr = 0;
                    while (cLen > (int)sizeof(struct heartbeat_chunk) + parptr) {
                        // we supppose type 1 here
                        const struct heartbeat_info *hbi = (struct heartbeat_info *)(((unsigned char *)hbc) + sizeof(struct heartbeat_chunk) + parptr);
                        if (ntohs(hbi->type) == 1) { // sender specific hb info
                            int32_t infoLen = ntohs(hbi->length) - 4;
                            parptr += ADD_PADDING(infoLen) + 4;
                            chunk->setInfoArraySize(infoLen);
                            for (int32_t i = 0; i < infoLen; i++)
                                chunk->setInfo(i, HBI_INFO(hbi)[i]);
                        }
                        else {
                            parptr += ADD_PADDING(ntohs(hbi->length)); // set pointer forwards with count of bytes in length field of TLV
                            continue;
                        }
                    }
                }
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case HEARTBEAT_ACK: {
                EV << "SctpHeader: Heartbeat_Ack received\n";
                const struct heartbeat_ack_chunk *hbac = (struct heartbeat_ack_chunk *)(chunks + chunkPtr);
                SctpHeartbeatAckChunk *chunk = new SctpHeartbeatAckChunk("HEARTBEAT_ACK");
                chunk->setSctpChunkType(chunkType);
                if (cLen > (int)sizeof(struct heartbeat_ack_chunk)) {
                    parptr = 0;
                    while (cLen > (int)sizeof(struct heartbeat_ack_chunk) + parptr) {
                        // we supppose type 1 here, the same provided in heartbeat chunks
                        const struct heartbeat_info *hbi = (struct heartbeat_info *)(((unsigned char *)hbac) + sizeof(struct heartbeat_ack_chunk) + parptr);
                        if (ntohs(hbi->type) == 1) { // sender specific hb info
                            uint16_t ilen = ntohs(hbi->length);
                            ASSERT(ilen >= 4 && ilen == cLen - sizeof(struct heartbeat_ack_chunk));
                            uint16_t infoLen = ilen - 4;
                            parptr += ADD_PADDING(infoLen) + 4;
                            chunk->setRemoteAddr(L3Address(Ipv4Address(ntohl(HBI_ADDR(hbi).v4addr.address))));
                            chunk->setTimeField(ntohl((uint32_t)HBI_TIME(hbi)));
                            chunk->setInfoArraySize(infoLen);
                            for (int32_t i = 0; i < infoLen; i++)
                                chunk->setInfo(i, HBI_INFO(hbi)[i]);
                        }
                        else {
                            parptr += ntohs(hbi->length); // set pointer forwards with count of bytes in length field of TLV
                            continue;
                        }
                    }
                }
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case ABORT: {
                EV << "SctpHeader: Abort received\n";
                const struct abort_chunk *ac = (struct abort_chunk *)(chunks + chunkPtr);
                cLen = ntohs(ac->length);
                SctpAbortChunk *chunk = new SctpAbortChunk("ABORT");
                chunk->setSctpChunkType(chunkType);
                chunk->setT_Bit(ac->flags & T_BIT);
                if (cLen > (int)sizeof(struct abort_chunk)) {
                    // TODO handle attached error causes
                }
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case COOKIE_ECHO: {
                SctpCookieEchoChunk *chunk = new SctpCookieEchoChunk("COOKIE_ECHO");
                chunk->setSctpChunkType(chunkType);
                EV_INFO << "Parse Cookie-Echo\n";
                if (cLen > (int)sizeof(struct cookie_echo_chunk)) {
                    int32_t cookieSize = woPadding - sizeof(struct cookie_echo_chunk);
                    EV_DETAIL << "cookieSize=" << cookieSize << "\n";
                    const struct cookie_parameter *cookie = (struct cookie_parameter *)(chunks + chunkPtr + 4);
                    SctpCookie *stateCookie = new SctpCookie();
                    stateCookie->setCreationTime(ntohl(cookie->creationTime));
                    stateCookie->setLocalTag(ntohl(cookie->localTag));
                    stateCookie->setPeerTag(ntohl(cookie->peerTag));
                    stateCookie->setLocalTieTagArraySize(32);
                    stateCookie->setPeerTieTagArraySize(32);
                    for (int32_t i = 0; i < 32; i++) {
                        stateCookie->setLocalTieTag(i, cookie->localTieTag[i]);
                        stateCookie->setPeerTieTag(i, cookie->peerTieTag[i]);
                    }
                    stateCookie->setLength(SCTP_COOKIE_LENGTH);
                    chunk->setStateCookie(stateCookie);
                }
                chunk->setBitLength(woPadding * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case COOKIE_ACK: {
                EV << "SctpHeader: Cookie_Ack received\n";
                SctpCookieAckChunk *chunk = new SctpCookieAckChunk("COOKIE_ACK");
                chunk->setSctpChunkType(chunkType);
                chunk->setByteLength(cLen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case SHUTDOWN: {
                EV << "SctpHeader: Shutdown received\n";
                const struct shutdown_chunk *sc = (struct shutdown_chunk *)(chunks + chunkPtr);
                SctpShutdownChunk *chunk = new SctpShutdownChunk("SHUTDOWN");
                chunk->setSctpChunkType(chunkType);
                uint32_t cumtsnack = ntohl(sc->cumulative_tsn_ack);
                chunk->setCumTsnAck(cumtsnack);
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case SHUTDOWN_ACK: {
                EV << "SctpHeader: ShutdownAck received\n";
                SctpShutdownAckChunk *chunk = new SctpShutdownAckChunk("SHUTDOWN_ACK");
                chunk->setSctpChunkType(chunkType);
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case SHUTDOWN_COMPLETE: {
                EV << "SctpHeader: ShutdownComplete received\n";
                const struct shutdown_complete_chunk *scc = (struct shutdown_complete_chunk *)(chunks + chunkPtr);
                SctpShutdownCompleteChunk *chunk = new SctpShutdownCompleteChunk("SHUTDOWN_COMPLETE");
                chunk->setSctpChunkType(chunkType);
                chunk->setTBit(scc->flags & T_BIT);
                chunk->setBitLength(cLen * 8);
                dest->appendSctpChunks(chunk);
                break;
            }

            case ERRORTYPE: {
                const struct error_chunk *error;
                error = (struct error_chunk *)(chunks + chunkPtr);
                SctpErrorChunk *errorchunk;
                errorchunk = new SctpErrorChunk("ERROR");
                errorchunk->setSctpChunkType(chunkType);
                errorchunk->setBitLength(SCTP_ERROR_CHUNK_LENGTH * 8);
                parptr = 0;
                const struct error_cause *err = (struct error_cause *)(((unsigned char *)error) + sizeof(struct error_chunk) + parptr);
                if (err->cause_code == UNSUPPORTED_HMAC) {
                    SctpSimpleErrorCauseParameter *errParam;
                    errParam = new SctpSimpleErrorCauseParameter();
                    errParam->setParameterType(err->cause_code);
                    errParam->setByteLength(err->length);
                    errorchunk->addParameters(errParam);
                }
                dest->appendSctpChunks(errorchunk);
                break;
            }

            case FORWARD_TSN: {
                EV << "SctpHeader: ForwardTsn received" << endl;
                const struct forward_tsn_chunk *forward_tsn_chunk;
                forward_tsn_chunk = (struct forward_tsn_chunk *)(chunks + chunkPtr);
                SctpForwardTsnChunk *chunk;
                chunk = new SctpForwardTsnChunk("FORWARD_TSN");
                chunk->setSctpChunkType(chunkType);
                chunk->setName("FORWARD_TSN");
                chunk->setNewCumTsn(ntohl(forward_tsn_chunk->cum_tsn));
                int streamNumber = 0, streamptr = 0;
                while (cLen > (int)sizeof(struct forward_tsn_chunk) + streamptr) {
                    const struct forward_tsn_streams *forward = (struct forward_tsn_streams *)(((unsigned char *)forward_tsn_chunk) + sizeof(struct forward_tsn_chunk) + streamptr);
                    chunk->setSidArraySize(++streamNumber);
                    chunk->setSid(streamNumber - 1, ntohs(forward->sid));
                    chunk->setSsnArraySize(streamNumber);
                    chunk->setSsn(streamNumber - 1, ntohs(forward->ssn));
                    streamptr += sizeof(struct forward_tsn_streams);
                }
                chunk->setByteLength(cLen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case AUTH: {
                int hmacSize;
                struct auth_chunk *ac = (struct auth_chunk *)(chunks + chunkPtr);
                SctpAuthenticationChunk *chunk = new SctpAuthenticationChunk("AUTH");
                chunk->setSctpChunkType(chunkType);
                chunk->setSharedKey(ntohs(ac->shared_key));
                chunk->setHMacIdentifier(ntohs(ac->hmac_identifier));
                if (cLen > (int)sizeof(struct auth_chunk)) {
                    hmacSize = woPadding - sizeof(struct auth_chunk);
                    chunk->setHMACArraySize(hmacSize);
                    for (int i = 0; i < hmacSize; i++) {
                        chunk->setHMAC(i, ac->hmac[i]);
                        ac->hmac[i] = 0;
                    }
                }

                unsigned char result[SHA_LENGTH];
                unsigned int flen;
                flen = bufsize - (sizeof(struct common_header) + chunkPtr);

                const struct data_vector *sc = (struct data_vector *)(chunks + chunkPtr);
                hmacSha1((uint8_t *)sc->data, flen, keys.sharedKey, keys.sizeKeyVector + keys.sizePeerKeyVector, result);

                chunk->setHMacOk(true);
                for (unsigned int j = 0; j < SHA_LENGTH; j++) {
                    if (result[j] != chunk->getHMAC(j)) {
                        EV_DETAIL << "hmac falsch\n";
                        chunk->setHMacOk(false);
                        break;
                    }
                }
                chunk->setByteLength(woPadding);
                dest->appendSctpChunks(chunk);
                break;
            }

            case ASCONF: {
                const struct asconf_chunk *asconf_chunk = (struct asconf_chunk *)(chunks + chunkPtr); // (recvBuffer + size_ip + sizeof(struct common_header));
                int paramLength = 0;
                SctpAsconfChunk *chunk = new SctpAsconfChunk("ASCONF");
                chunk->setSctpChunkType(chunkType);
                chunk->setName("ASCONF");
                chunk->setSerialNumber(ntohl(asconf_chunk->serial));
                if (cLen > (int)sizeof(struct asconf_chunk)) {
                    parptr = 0;
                    // we supppose an ipv4 address parameter
                    const struct init_ipv4_address_parameter *ipv4addr = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf_chunk) + sizeof(struct asconf_chunk) + parptr);
                    int parlen = ADD_PADDING(ntohs(ipv4addr->length));
                    parptr += parlen;
                    // set pointer forwards with count of bytes in length field of TLV
                    if (ntohs(ipv4addr->type) != INIT_PARAM_IPV4) {
                        if (parlen == 0)
                            throw cRuntimeError("ParamLen == 0.");
                        continue;
                    }
                    else {
                        L3Address localAddr(Ipv4Address(ntohl(ipv4addr->address)));
                        chunk->setAddressParam(localAddr);
                    }
                    while (cLen > (int)sizeof(struct asconf_chunk) + parptr) {
                        const struct add_ip_parameter *ipparam = (struct add_ip_parameter *)(((unsigned char *)asconf_chunk) + sizeof(struct asconf_chunk) + parptr);
                        paramType = ntohs(ipparam->type);
                        paramLength = ntohs(ipparam->length);
                        switch (paramType) {
                            case ADD_IP_ADDRESS: {
                                EV_INFO << "parse ADD_IP_ADDRESS\n";
                                SctpAddIPParameter *addip;
                                addip = new SctpAddIPParameter("ADD_IP");
                                addip->setParameterType(ntohs(ipparam->type));
                                addip->setRequestCorrelationId(ntohl(ipparam->correlation_id));
                                const struct init_ipv4_address_parameter *v4addr1;
                                v4addr1 = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf_chunk) + sizeof(struct asconf_chunk) + parptr + sizeof(struct add_ip_parameter));
                                L3Address localAddr(Ipv4Address(ntohl(v4addr1->address)));
                                addip->setAddressParam(localAddr);
                                chunk->addAsconfParam(addip);
                                break;
                            }

                            case DELETE_IP_ADDRESS: {
                                EV_INFO << "parse DELETE_IP_ADDRESS\n";
                                SctpDeleteIPParameter *deleteip;
                                deleteip = new SctpDeleteIPParameter("DELETE_IP");
                                deleteip->setParameterType(ntohs(ipparam->type));
                                deleteip->setRequestCorrelationId(ntohl(ipparam->correlation_id));
                                const struct init_ipv4_address_parameter *v4addr2;
                                v4addr2 = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf_chunk) + sizeof(struct asconf_chunk) + parptr + sizeof(struct add_ip_parameter));
                                L3Address localAddr(Ipv4Address(ntohl(v4addr2->address)));
                                deleteip->setAddressParam(localAddr);
                                chunk->addAsconfParam(deleteip);
                                break;
                            }

                            case SET_PRIMARY_ADDRESS: {
                                EV_INFO << "parse SET_PRIMARY_ADDRESS\n";
                                SctpSetPrimaryIPParameter *priip;
                                priip = new SctpSetPrimaryIPParameter("SET_PRI_IP");
                                priip->setParameterType(ntohs(ipparam->type));
                                priip->setRequestCorrelationId(ntohl(ipparam->correlation_id));
                                const struct init_ipv4_address_parameter *v4addr3;
                                v4addr3 = (struct init_ipv4_address_parameter *)(((unsigned char *)asconf_chunk) + sizeof(struct asconf_chunk) + parptr + sizeof(struct add_ip_parameter));
                                L3Address localAddr(Ipv4Address(ntohl(v4addr3->address)));
                                priip->setAddressParam(localAddr);
                                chunk->addAsconfParam(priip);
                                break;
                            }

                            default:
                                EV << "Unknown Sctp parameter type " << paramType;
                                /*throw cRuntimeError("TODO unknown parametertype in incoming packet from external interface! Implement it!");*/
                                break;
                        }
                        parptr += ADD_PADDING(paramLength);
                    }
                }
                chunk->setByteLength(cLen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case ASCONF_ACK: {
                const struct asconf_ack_chunk *asconf_ack_chunk = (struct asconf_ack_chunk *)(chunks + chunkPtr); // (recvBuffer + size_ip + sizeof(struct common_header));
                int paramLength = 0;
                SctpAsconfAckChunk *chunk = new SctpAsconfAckChunk("ASCONF_ACK");
                chunk->setSctpChunkType(chunkType);
                chunk->setName("ASCONF_ACK");
                chunk->setSerialNumber(ntohl(asconf_ack_chunk->serial));
                if (cLen > (int)sizeof(struct asconf_ack_chunk)) {
                    parptr = 0;

                    while (cLen > (int)sizeof(struct asconf_ack_chunk) + parptr) {
                        const struct add_ip_parameter *ipparam = (struct add_ip_parameter *)(((unsigned char *)asconf_ack_chunk) + sizeof(struct asconf_ack_chunk) + parptr);
                        paramType = ntohs(ipparam->type);
                        paramLength = ntohs(ipparam->length);
                        switch (paramType) {
                            case ERROR_CAUSE_INDICATION: {
                                SctpErrorCauseParameter *errorip;
                                errorip = new SctpErrorCauseParameter("ERROR_CAUSE");
                                errorip->setParameterType(ntohs(ipparam->type));
                                errorip->setResponseCorrelationId(ntohl(ipparam->correlation_id));
                                const struct error_cause *errorcause;
                                errorcause = (struct error_cause *)(((unsigned char *)asconf_ack_chunk) + sizeof(struct asconf_ack_chunk) + parptr + sizeof(struct add_ip_parameter));
                                errorip->setErrorCauseType(htons(errorcause->cause_code));
                                chunk->addAsconfResponse(errorip);
                                break;
                            }

                            case SUCCESS_INDICATION: {
                                SctpSuccessIndication *success;
                                success = new SctpSuccessIndication("SUCCESS");
                                success->setParameterType(ntohs(ipparam->type));
                                success->setResponseCorrelationId(ntohl(ipparam->correlation_id));
                                chunk->addAsconfResponse(success);
                                break;
                            }

                            default:
                                EV << "Unknown Sctp parameter type " << paramType;
                                break;
                        }
                        parptr += ADD_PADDING(paramLength);
                    }
                }
                chunk->setByteLength(cLen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case RE_CONFIG: {
                const struct stream_reset_chunk *stream_reset_chunk;
                stream_reset_chunk = (struct stream_reset_chunk *)(chunks + chunkPtr);
                SctpStreamResetChunk *chunk;
                chunk = new SctpStreamResetChunk("RE_CONFIG");
                chunk->setSctpChunkType(chunkType);
                chunk->setName("RE_CONFIG");
                chunk->setByteLength(SCTP_STREAM_RESET_CHUNK_LENGTH);
                chunklen = SCTP_STREAM_RESET_CHUNK_LENGTH;
                int len;
                if ((unsigned int)cLen > sizeof(struct stream_reset_chunk)) {
                    parptr = 0;
                    int snnumbers, sncounter;
                    while (cLen > (int)sizeof(struct stream_reset_chunk) + parptr) {
                        const struct tlv *parameter = (struct tlv *)(((unsigned char *)stream_reset_chunk) + sizeof(struct stream_reset_chunk) + parptr);
                        paramType = ntohs(parameter->type);
                        int paramLength = ntohs(parameter->length);
                        switch (paramType) {
                            case OUTGOING_RESET_REQUEST_PARAMETER: {
                                const struct outgoing_reset_request_parameter *outrr;
                                outrr = (struct outgoing_reset_request_parameter *)(((unsigned char *)stream_reset_chunk) + sizeof(struct stream_reset_chunk) + parptr);
                                SctpOutgoingSsnResetRequestParameter *outstrrst;
                                outstrrst = new SctpOutgoingSsnResetRequestParameter("OUT_STR_RST");
                                outstrrst->setParameterType(OUTGOING_RESET_REQUEST_PARAMETER);
                                outstrrst->setSrReqSn(ntohl(outrr->srReqSn)); // Stream Reset Request Sequence Number
                                outstrrst->setSrResSn(ntohl(outrr->srResSn)); // Stream Reset Response Sequence Number
                                outstrrst->setLastTsn(ntohl(outrr->lastTsn)); // Senders last assigned TSN
                                chunklen += SCTP_OUTGOING_RESET_REQUEST_PARAMETER_LENGTH;
                                len = SCTP_OUTGOING_RESET_REQUEST_PARAMETER_LENGTH;
                                sncounter = 0;
                                while (ntohs(outrr->length) > len) {
                                    snnumbers = (int)*(chunks + chunkPtr + sizeof(struct stream_reset_chunk) + parptr + SCTP_OUTGOING_RESET_REQUEST_PARAMETER_LENGTH + sncounter * 2);
                                    outstrrst->setStreamNumbersArraySize(++sncounter);
                                    outstrrst->setStreamNumbers(sncounter - 1, snnumbers);
                                    chunklen += 2;
                                    len += 2;
                                }
                                chunk->addParameter(outstrrst);
                                break;
                            }

                            case INCOMING_RESET_REQUEST_PARAMETER: {
                                const struct incoming_reset_request_parameter *inrr;
                                inrr = (struct incoming_reset_request_parameter *)(((unsigned char *)stream_reset_chunk) + sizeof(struct stream_reset_chunk) + parptr);
                                SctpIncomingSsnResetRequestParameter *instrrst;
                                instrrst = new SctpIncomingSsnResetRequestParameter("IN_STR_RST");
                                instrrst->setParameterType(INCOMING_RESET_REQUEST_PARAMETER);
                                instrrst->setSrReqSn(ntohl(inrr->srReqSn)); // Stream Reset Request Sequence Number
                                chunklen += SCTP_OUTGOING_RESET_REQUEST_PARAMETER_LENGTH;
                                len = SCTP_INCOMING_RESET_REQUEST_PARAMETER_LENGTH;
                                sncounter = 0;
                                while (ntohs(inrr->length) > len) {
                                    snnumbers = (int)*(chunks + chunkPtr + sizeof(struct stream_reset_chunk) + parptr + SCTP_OUTGOING_RESET_REQUEST_PARAMETER_LENGTH + sncounter * 2);
                                    instrrst->setStreamNumbersArraySize(++sncounter);
                                    instrrst->setStreamNumbers(sncounter - 1, snnumbers);
                                    chunklen += 2;
                                    len += 2;
                                }
                                chunk->addParameter(instrrst);
                                break;
                            }

                            case SSN_TSN_RESET_REQUEST_PARAMETER: {
                                const struct ssn_tsn_reset_request_parameter *ssnrr;
                                ssnrr = (struct ssn_tsn_reset_request_parameter *)(((unsigned char *)stream_reset_chunk) + sizeof(struct stream_reset_chunk) + parptr);
                                SctpSsnTsnResetRequestParameter *ssnstrrst;
                                ssnstrrst = new SctpSsnTsnResetRequestParameter("SSN_STR_RST");
                                ssnstrrst->setParameterType(SSN_TSN_RESET_REQUEST_PARAMETER);
                                ssnstrrst->setSrReqSn(ntohl(ssnrr->srReqSn));
                                chunklen += SCTP_SSN_TSN_RESET_REQUEST_PARAMETER_LENGTH;
                                chunk->addParameter(ssnstrrst);
                                break;
                            }

                            case STREAM_RESET_RESPONSE_PARAMETER: {
                                const struct stream_reset_response_parameter *resp;
                                resp = (struct stream_reset_response_parameter *)(((unsigned char *)stream_reset_chunk) + sizeof(struct stream_reset_chunk) + parptr);
                                SctpStreamResetResponseParameter *strrst;
                                strrst = new SctpStreamResetResponseParameter("STR_RST_RESPONSE");
                                strrst->setParameterType(STREAM_RESET_RESPONSE_PARAMETER);
                                strrst->setSrResSn(ntohl(resp->srResSn));
                                strrst->setResult(ntohl(resp->result));
                                int pLen = SCTP_STREAM_RESET_RESPONSE_PARAMETER_LENGTH;
                                if (cLen > (int)sizeof(struct stream_reset_chunk) + parptr + SCTP_STREAM_RESET_RESPONSE_PARAMETER_LENGTH) {
                                    strrst->setSendersNextTsn(ntohl(resp->sendersNextTsn));
                                    strrst->setReceiversNextTsn(ntohl(resp->receiversNextTsn));
                                    pLen += 8;
                                }
                                strrst->setByteLength(pLen);
                                chunk->addParameter(strrst);
                                break;
                            }
                        }
                        parptr += ADD_PADDING(paramLength);
                    }
                }
                chunk->setByteLength(cLen);
                dest->appendSctpChunks(chunk);
                break;
            }

            case PKTDROP: {
             /*   const struct pktdrop_chunk *drop;
                drop = (struct pktdrop_chunk *)(chunks + chunkPtr);
                SctpPacketDropChunk *dropChunk;
                dropChunk = new SctpPacketDropChunk("PKTDROP");
                dropChunk->setSctpChunkType(PKTDROP);
                dropChunk->setCFlag(drop->flags & C_FLAG);
                dropChunk->setTFlag(drop->flags & T_FLAG);
                dropChunk->setBFlag(drop->flags & B_FLAG);
                dropChunk->setMFlag(drop->flags & M_FLAG);
                dropChunk->setMaxRwnd(ntohl(drop->max_rwnd));
                dropChunk->setQueuedData(ntohl(drop->queued_data));
                dropChunk->setTruncLength(ntohs(drop->trunc_length));
                EV_INFO << "SctpSerializer::pktdrop: parse SctpHeader\n";
                SctpHeader *msg;
                msg = new SctpHeader();
                parse((unsigned char *)chunks + chunkPtr + 16, bufsize - sizeof(struct common_header) - chunkPtr - 16, msg);*/
                break;
            }

            default:
                EV_ERROR << "Parser: Unknown SCTP chunk type " << chunkType;
                break;
        } // end of switch(chunkType)
        chunkPtr += cLen;
    } // end of while()
    EV_INFO << "SctpSerializer - pkt info - " << dest->getChunkLength().get<B>() << " bytes" << endl;
    delete [] buffer;
    return dest;
}

bool SctpHeaderSerializer::compareRandom()
{
    unsigned int i, size;
    if (keys.sizeKeyVector != keys.sizePeerKeyVector) {
        if (keys.sizePeerKeyVector > keys.sizeKeyVector) {
            return false;
        }
        else {
            return true;
        }
    }
    else
        size = keys.sizeKeyVector;
    for (i = 0; i < size; i++) {
        if (keys.keyVector[i] < keys.peerKeyVector[i])
            return false;
        if (keys.keyVector[i] > keys.peerKeyVector[i])
            return true;
    }
    return true;
}

void SctpHeaderSerializer::calculateSharedKey()
{
    unsigned int i;
    bool peerFirst = false;

    peerFirst = compareRandom();

    if (peerFirst == false) {
        for (i = 0; i < keys.sizeKeyVector; i++)
            keys.sharedKey[i] = keys.keyVector[i];
        for (i = 0; i < keys.sizePeerKeyVector; i++)
            keys.sharedKey[i + keys.sizeKeyVector] = keys.peerKeyVector[i];
    }
    else {
        for (i = 0; i < keys.sizePeerKeyVector; i++)
            keys.sharedKey[i] = keys.peerKeyVector[i];
        for (i = 0; i < keys.sizeKeyVector; i++)
            keys.sharedKey[i + keys.sizePeerKeyVector] = keys.keyVector[i];
    }
}

} // namespace sctp

} // namespace inet

